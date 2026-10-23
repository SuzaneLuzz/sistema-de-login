"""
Sistema de Login — projeto full stack de autenticação
Autora: Suzane Luz · github.com/SuzaneLuzz

Login com e-mail e senha, Google e GitHub (OAuth 2.0).
Backend: Python + Flask + SQLite | Frontend: HTML, CSS e JavaScript
"""

import os
import re
import secrets
import sys
import threading
import uuid
import webbrowser
from datetime import datetime, timedelta

if sys.version_info < (3, 9):
    sys.exit("[ERRO] Este projeto precisa do Python 3.9 ou mais novo. "
             "Baixe a versão atual em python.org.")

# Mostra uma mensagem clara se as bibliotecas não estiverem instaladas
try:
    from authlib.integrations.flask_client import OAuth
    from dotenv import load_dotenv
    from flask import (Flask, abort, flash, redirect, render_template, request,
                       session, url_for)
    from flask_login import (LoginManager, current_user, login_required,
                             login_user, logout_user)
    from werkzeug.exceptions import RequestEntityTooLarge
    from werkzeug.security import check_password_hash, generate_password_hash
    from werkzeug.utils import secure_filename
except ImportError as erro:
    sys.exit(
        f"\n[ERRO] Biblioteca não encontrada: {erro.name}\n\n"
        "As dependências não estão instaladas no Python que está rodando o projeto.\n"
        "Solução mais fácil: dê dois cliques no arquivo iniciar.bat\n"
        "Ou, no terminal, dentro da pasta do projeto, rode:\n"
        f'    "{sys.executable}" -m pip install -r requirements.txt\n'
    )

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)  # funciona mesmo se for executado de outra pasta

from models import User, db  # noqa: E402

load_dotenv(os.path.join(BASE_DIR, ".env"))
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
EXTENSOES_PERMITIDAS = {"png", "jpg", "jpeg", "webp"}
AVATARES = [f"avatars/avatar{i}.svg" for i in range(1, 8)]

MAX_TENTATIVAS = 5
TEMPO_BLOQUEIO = timedelta(minutes=5)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# ---------------------------------------------------------------------------
# Configuração do app
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or secrets.token_hex(32)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "database.db")
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # upload de até 2 MB
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Faça login para acessar esta página."


@login_manager.user_loader
def carregar_usuario(user_id):
    return db.session.get(User, int(user_id))


# ---------------------------------------------------------------------------
# OAuth (Google e GitHub) — só é ativado se as chaves estiverem no .env
# ---------------------------------------------------------------------------

oauth = OAuth(app)
PROVEDORES = {}

if os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"):
    oauth.register(
        name="google",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    PROVEDORES["google"] = "Google"

if os.getenv("GITHUB_CLIENT_ID") and os.getenv("GITHUB_CLIENT_SECRET"):
    oauth.register(
        name="github",
        client_id=os.getenv("GITHUB_CLIENT_ID"),
        client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "read:user user:email"},
    )
    PROVEDORES["github"] = "GitHub"


# ---------------------------------------------------------------------------
# Proteção CSRF (impede que outros sites enviem formulários em seu nome)
# ---------------------------------------------------------------------------

def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def verificar_csrf():
    if request.method == "POST":
        enviado = request.form.get("_csrf", "")
        esperado = session.get("_csrf", "")
        if not esperado or not secrets.compare_digest(enviado, esperado):
            abort(400, "Token de segurança inválido. Recarregue a página.")


@app.errorhandler(RequestEntityTooLarge)
def arquivo_grande(_erro):
    flash("A imagem deve ter no máximo 2 MB.", "erro")
    return redirect(url_for("cadastro"))


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------

def validar_senha(senha):
    problemas = []
    if len(senha) < 8:
        problemas.append("ter pelo menos 8 caracteres")
    if not re.search(r"[A-Z]", senha):
        problemas.append("ter uma letra maiúscula")
    if not re.search(r"[a-z]", senha):
        problemas.append("ter uma letra minúscula")
    if not re.search(r"\d", senha):
        problemas.append("ter um número")
    return problemas


def salvar_upload(arquivo):
    """Salva a foto enviada com um nome aleatório e devolve o caminho relativo."""
    nome = secure_filename(arquivo.filename or "")
    extensao = nome.rsplit(".", 1)[-1].lower() if "." in nome else ""
    if extensao not in EXTENSOES_PERMITIDAS:
        return None
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    novo_nome = f"{uuid.uuid4().hex}.{extensao}"
    arquivo.save(os.path.join(UPLOAD_DIR, novo_nome))
    return f"uploads/{novo_nome}"


def entrar(usuario):
    usuario.last_login = datetime.now()
    usuario.failed_attempts = 0
    usuario.locked_until = None
    db.session.commit()
    session.clear()  # nova sessão a cada login (evita fixação de sessão)
    login_user(usuario, remember=True)


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------

@app.route("/")
def inicio():
    if current_user.is_authenticated:
        return redirect(url_for("painel"))
    return redirect(url_for("login"))


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if current_user.is_authenticated:
        return redirect(url_for("painel"))

    if request.method == "POST":
        nome = request.form.get("first_name", "").strip()
        sobrenome = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("password", "")
        confirmar = request.form.get("confirm_password", "")
        avatar = request.form.get("avatar", "")

        erros = []
        if not nome:
            erros.append("Informe seu primeiro nome.")
        if not EMAIL_RE.match(email):
            erros.append("Informe um e-mail válido.")
        elif User.query.filter_by(email=email).first():
            erros.append("Já existe uma conta com esse e-mail.")
        problemas = validar_senha(senha)
        if problemas:
            erros.append("A senha precisa " + ", ".join(problemas) + ".")
        if senha != confirmar:
            erros.append("As senhas não coincidem.")

        caminho_avatar = None
        if avatar == "upload":
            arquivo = request.files.get("avatar_file")
            if arquivo and arquivo.filename:
                caminho_avatar = salvar_upload(arquivo)
                if not caminho_avatar:
                    erros.append("Foto inválida. Use PNG, JPG ou WEBP.")
        elif avatar in AVATARES:
            caminho_avatar = avatar

        if erros:
            for erro in erros:
                flash(erro, "erro")
            return render_template("cadastro.html", form=request.form,
                                   avatares=AVATARES, provedores=PROVEDORES)

        usuario = User(
            first_name=nome,
            last_name=sobrenome,
            email=email,
            password_hash=generate_password_hash(senha),
            avatar=caminho_avatar,
        )
        db.session.add(usuario)
        db.session.commit()
        entrar(usuario)
        flash("Conta criada com sucesso. Bem-vindo(a)!", "sucesso")
        return redirect(url_for("painel"))

    return render_template("cadastro.html", form={}, avatares=AVATARES,
                           provedores=PROVEDORES)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("painel"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("password", "")
        usuario = User.query.filter_by(email=email).first()

        if usuario and usuario.locked_until and usuario.locked_until > datetime.now():
            minutos = int((usuario.locked_until - datetime.now()).total_seconds() // 60) + 1
            flash(f"Conta bloqueada por excesso de tentativas. Tente em {minutos} min.", "erro")
        elif usuario and not usuario.password_hash:
            flash("Esta conta usa login com Google ou GitHub.", "erro")
        elif usuario and check_password_hash(usuario.password_hash, senha):
            entrar(usuario)
            return redirect(url_for("painel"))
        else:
            if usuario:
                usuario.failed_attempts = (usuario.failed_attempts or 0) + 1
                if usuario.failed_attempts >= MAX_TENTATIVAS:
                    usuario.locked_until = datetime.now() + TEMPO_BLOQUEIO
                    usuario.failed_attempts = 0
                db.session.commit()
            # Mensagem genérica: não revela se o e-mail existe
            flash("E-mail ou senha incorretos.", "erro")

        return render_template("login.html", form=request.form, provedores=PROVEDORES)

    return render_template("login.html", form={}, provedores=PROVEDORES)


@app.route("/login/<provedor>")
def login_externo(provedor):
    if provedor not in ("google", "github"):
        abort(404)
    if provedor not in PROVEDORES:
        flash(f"Login com {provedor.title()} ainda não foi configurado. Veja o README.", "erro")
        return redirect(request.referrer or url_for("login"))
    retorno = url_for("callback_externo", provedor=provedor, _external=True)
    return oauth.create_client(provedor).authorize_redirect(retorno)


@app.route("/auth/<provedor>/callback")
def callback_externo(provedor):
    if provedor not in PROVEDORES:
        abort(404)
    cliente = oauth.create_client(provedor)

    try:
        token = cliente.authorize_access_token()
    except Exception:
        flash("Não foi possível concluir o login. Tente novamente.", "erro")
        return redirect(url_for("login"))

    if provedor == "google":
        info = token.get("userinfo") or cliente.userinfo()
        id_externo = str(info["sub"])
        email = info.get("email") if info.get("email_verified") else None
        nome = info.get("given_name") or info.get("name") or "Usuário"
        sobrenome = info.get("family_name", "")
        foto = info.get("picture")
    else:
        info = cliente.get("user", token=token).json()
        id_externo = str(info["id"])
        emails = cliente.get("user/emails", token=token).json()
        email = next((e["email"] for e in emails
                      if e.get("primary") and e.get("verified")), None)
        partes = (info.get("name") or info.get("login") or "Usuário").split(" ", 1)
        nome, sobrenome = partes[0], (partes[1] if len(partes) > 1 else "")
        foto = info.get("avatar_url")

    if not email:
        flash(f"Sua conta {PROVEDORES[provedor]} não tem um e-mail verificado.", "erro")
        return redirect(url_for("login"))

    campo_id = f"{provedor}_id"
    email = email.lower()
    usuario = (User.query.filter(getattr(User, campo_id) == id_externo).first()
               or User.query.filter_by(email=email).first())

    conta_nova = usuario is None
    if conta_nova:
        usuario = User(first_name=nome, last_name=sobrenome, email=email, avatar=foto)
        db.session.add(usuario)
    elif not usuario.avatar and foto:
        usuario.avatar = foto

    # Vincula a conta externa (permite entrar por mais de um método)
    setattr(usuario, campo_id, id_externo)
    db.session.commit()
    entrar(usuario)
    if conta_nova:
        flash(f"Conta criada com {PROVEDORES[provedor]}. Bem-vindo(a)!", "sucesso")
    return redirect(url_for("painel"))


@app.route("/painel")
@login_required
def painel():
    return render_template("painel.html", usuario=current_user)


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    logout_user()  # depois do clear, para também apagar o cookie "lembrar de mim"
    flash("Você saiu da sua conta.", "sucesso")
    return redirect(url_for("login"))


with app.app_context():
    db.create_all()


def abrir_navegador_quando_pronto(endereco, limite=60):
    """Espera o servidor aceitar conexões antes de abrir o navegador."""
    import socket
    import time

    for _ in range(limite * 4):
        try:
            with socket.create_connection(("127.0.0.1", 5000), timeout=0.5):
                webbrowser.open(endereco)
                return
        except OSError:
            time.sleep(0.25)
    print("[AVISO] O servidor demorou para iniciar. Veja se há erros acima.")


if __name__ == "__main__":
    ENDERECO = "http://127.0.0.1:5000"

    # Abre o navegador sozinho (só uma vez, mesmo com o recarregamento automático)
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        print("\n" + "=" * 50)
        print("  Sistema de Login rodando!")
        print(f"  Acesse: {ENDERECO}")
        print("  Para parar o servidor: Ctrl + C")
        print("=" * 50 + "\n")
        threading.Thread(target=abrir_navegador_quando_pronto,
                         args=(ENDERECO,), daemon=True).start()

    try:
        app.run(host="127.0.0.1", port=5000, debug=True)
    except OSError:
        sys.exit("[ERRO] A porta 5000 já está em uso. Feche o outro terminal "
                 "que está rodando o projeto e tente de novo.")
