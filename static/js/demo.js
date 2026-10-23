/*
 * Sistema de Login — versão de demonstração para o GitHub Pages
 *
 * O GitHub Pages só hospeda arquivos estáticos (não roda Python), então esta
 * versão faz em JavaScript o que o servidor Flask faz no projeto completo:
 * cadastro, login, hash de senha (PBKDF2), bloqueio por tentativas e sessão.
 * Os dados ficam salvos apenas no navegador de quem acessa (localStorage).
 */

const CHAVE_USUARIOS = "sistemaLogin.usuarios";
const CHAVE_SESSAO = "sistemaLogin.sessao";
const MAX_TENTATIVAS = 5;
const TEMPO_BLOQUEIO_MS = 5 * 60 * 1000;
const AVATARES = [1, 2, 3, 4, 5, 6, 7].map((i) => `static/avatars/avatar${i}.svg`);
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

// ---------------------------------------------------------------------------
// Armazenamento (protegido com try/catch: o navegador pode bloquear)
// ---------------------------------------------------------------------------

function ler(chave, padrao) {
  try {
    const valor = localStorage.getItem(chave);
    return valor ? JSON.parse(valor) : padrao;
  } catch {
    return padrao;
  }
}

function gravar(chave, valor) {
  try {
    localStorage.setItem(chave, JSON.stringify(valor));
    return true;
  } catch {
    return false;
  }
}

function apagar(chave) {
  try { localStorage.removeItem(chave); } catch { /* ignora */ }
}

const usuarios = () => ler(CHAVE_USUARIOS, {});
const salvarUsuarios = (lista) => gravar(CHAVE_USUARIOS, lista);
const usuarioLogado = () => {
  const email = ler(CHAVE_SESSAO, null);
  return email ? usuarios()[email] || null : null;
};

// ---------------------------------------------------------------------------
// Segurança: hash da senha com PBKDF2 + salt (Web Crypto API)
// ---------------------------------------------------------------------------

const paraHex = (buffer) =>
  [...new Uint8Array(buffer)].map((b) => b.toString(16).padStart(2, "0")).join("");
const deHex = (hex) => new Uint8Array(hex.match(/.{2}/g).map((h) => parseInt(h, 16)));

async function gerarHash(senha, saltHex) {
  const salt = saltHex ? deHex(saltHex) : crypto.getRandomValues(new Uint8Array(16));
  const chave = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(senha), "PBKDF2", false, ["deriveBits"]
  );
  const bits = await crypto.subtle.deriveBits(
    { name: "PBKDF2", salt, iterations: 100000, hash: "SHA-256" }, chave, 256
  );
  return { hash: paraHex(bits), salt: paraHex(salt) };
}

function problemasSenha(senha) {
  const problemas = [];
  if (senha.length < 8) problemas.push("ter pelo menos 8 caracteres");
  if (!/[A-Z]/.test(senha)) problemas.push("ter uma letra maiúscula");
  if (!/[a-z]/.test(senha)) problemas.push("ter uma letra minúscula");
  if (!/\d/.test(senha)) problemas.push("ter um número");
  return problemas;
}

// ---------------------------------------------------------------------------
// Avisos (mensagens de erro e sucesso)
// ---------------------------------------------------------------------------

const caixaAvisos = document.getElementById("avisos");
let avisosPendentes = [];

function avisar(mensagem, tipo = "erro") {
  avisosPendentes.push({ mensagem, tipo });
}

function mostrarAvisos() {
  caixaAvisos.innerHTML = "";
  avisosPendentes.forEach(({ mensagem, tipo }) => {
    const div = document.createElement("div");
    div.className = `aviso aviso-${tipo}`;
    div.setAttribute("role", "alert");
    div.textContent = mensagem;
    caixaAvisos.appendChild(div);
  });
  caixaAvisos.hidden = avisosPendentes.length === 0;
  avisosPendentes = [];
}

// ---------------------------------------------------------------------------
// Navegação entre as telas (#login, #cadastro, #painel)
// ---------------------------------------------------------------------------

const TITULOS = { login: "Entrar", cadastro: "Criar conta", painel: "Meu perfil" };

function ir(tela) {
  if (location.hash === `#${tela}`) navegar();
  else location.hash = tela;
}

function navegar() {
  let tela = location.hash.slice(1) || "login";
  if (!TITULOS[tela]) tela = "login";

  const logado = usuarioLogado();
  if (tela === "painel" && !logado) {
    avisar("Faça login para acessar esta página.");
    tela = "login";
  } else if (tela !== "painel" && logado) {
    tela = "painel";
  }
  if (location.hash.slice(1) !== tela) history.replaceState(null, "", `#${tela}`);

  document.querySelectorAll("[data-tela]").forEach((secao) => {
    secao.hidden = secao.dataset.tela !== tela;
  });
  document.getElementById("caixa").classList.toggle("caixa-estreita", tela !== "cadastro");
  document.title = `${TITULOS[tela]} · Sistema de Login`;

  if (tela === "painel") preencherPainel(logado);
  mostrarAvisos();
  window.scrollTo(0, 0);
}

window.addEventListener("hashchange", navegar);

// ---------------------------------------------------------------------------
// Avatares
// ---------------------------------------------------------------------------

const listaAvatares = document.getElementById("lista-avatares");
AVATARES.forEach((caminho, i) => {
  const label = document.createElement("label");
  label.className = "avatar-opcao";
  label.title = `Avatar ${i + 1}`;
  label.innerHTML = `<input type="radio" name="avatar" value="${caminho}">
    <img class="avatar-forma" src="${caminho}" alt="Avatar ${i + 1}">`;
  listaAvatares.appendChild(label);
});

// Reduz a foto enviada para caber no armazenamento do navegador
function reduzirFoto(arquivo, tamanho = 160) {
  return new Promise((resolve, reject) => {
    const leitor = new FileReader();
    leitor.onerror = reject;
    leitor.onload = () => {
      const img = new Image();
      img.onerror = reject;
      img.onload = () => {
        const canvas = document.createElement("canvas");
        canvas.width = canvas.height = tamanho;
        const lado = Math.min(img.width, img.height);
        canvas.getContext("2d").drawImage(
          img, (img.width - lado) / 2, (img.height - lado) / 2, lado, lado,
          0, 0, tamanho, tamanho
        );
        resolve(canvas.toDataURL("image/jpeg", 0.85));
      };
      img.src = leitor.result;
    };
    leitor.readAsDataURL(arquivo);
  });
}

// ---------------------------------------------------------------------------
// Cadastro
// ---------------------------------------------------------------------------

document.getElementById("form-cadastro").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const valor = (id) => document.getElementById(id).value.trim();

  const nome = valor("first_name");
  const sobrenome = valor("last_name");
  const email = valor("email").toLowerCase();
  const senha = document.getElementById("password").value;
  const confirmar = document.getElementById("confirm_password").value;
  const escolhido = document.querySelector('input[name="avatar"]:checked');
  const lista = usuarios();

  const erros = [];
  if (!nome) erros.push("Informe seu primeiro nome.");
  if (!EMAIL_RE.test(email)) erros.push("Informe um e-mail válido.");
  else if (lista[email]) erros.push("Já existe uma conta com esse e-mail.");
  const problemas = problemasSenha(senha);
  if (problemas.length) erros.push(`A senha precisa ${problemas.join(", ")}.`);
  if (senha !== confirmar) erros.push("As senhas não coincidem.");

  let avatar = null;
  if (escolhido?.value === "upload") {
    const arquivo = document.getElementById("avatar_file").files[0];
    if (arquivo) {
      try { avatar = await reduzirFoto(arquivo); }
      catch { erros.push("Não foi possível ler a foto. Use PNG, JPG ou WEBP."); }
    }
  } else if (escolhido) {
    avatar = escolhido.value;
  }

  if (erros.length) {
    erros.forEach((e) => avisar(e));
    mostrarAvisos();
    window.scrollTo({ top: 0, behavior: "smooth" });
    return;
  }

  let protegida;
  try {
    protegida = await gerarHash(senha);
  } catch {
    avisar("Seu navegador não permite criptografia nesta página. Abra pelo link do GitHub Pages (https).");
    mostrarAvisos();
    return;
  }

  const agora = new Date().toISOString();
  lista[email] = {
    nome, sobrenome, email, avatar,
    hash: protegida.hash, salt: protegida.salt,
    tentativas: 0, bloqueadoAte: 0,
    criadoEm: agora, ultimoAcesso: agora,
  };

  if (!salvarUsuarios(lista) || !gravar(CHAVE_SESSAO, email)) {
    avisar("O navegador bloqueou o armazenamento de dados. Desative o modo anônimo e tente de novo.");
    mostrarAvisos();
    return;
  }

  evento.target.reset();
  document.querySelector(".avatar-upload")?.classList.remove("com-foto");
  document.getElementById("preview-upload").style.backgroundImage = "";
  avisar("Conta criada com sucesso. Bem-vindo(a)!", "sucesso");
  ir("painel");
});

// ---------------------------------------------------------------------------
// Login
// ---------------------------------------------------------------------------

document.getElementById("form-login").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const email = document.getElementById("login_email").value.trim().toLowerCase();
  const senha = document.getElementById("login_password").value;
  const lista = usuarios();
  const usuario = lista[email];

  if (usuario && usuario.bloqueadoAte > Date.now()) {
    const minutos = Math.ceil((usuario.bloqueadoAte - Date.now()) / 60000);
    avisar(`Conta bloqueada por excesso de tentativas. Tente em ${minutos} min.`);
    mostrarAvisos();
    return;
  }

  let senhaCerta = false;
  if (usuario) {
    try {
      senhaCerta = (await gerarHash(senha, usuario.salt)).hash === usuario.hash;
    } catch { senhaCerta = false; }
  }

  if (senhaCerta) {
    usuario.tentativas = 0;
    usuario.bloqueadoAte = 0;
    usuario.ultimoAcesso = new Date().toISOString();
    salvarUsuarios(lista);
    gravar(CHAVE_SESSAO, email);
    evento.target.reset();
    ir("painel");
    return;
  }

  if (usuario) {
    usuario.tentativas = (usuario.tentativas || 0) + 1;
    if (usuario.tentativas >= MAX_TENTATIVAS) {
      usuario.bloqueadoAte = Date.now() + TEMPO_BLOQUEIO_MS;
      usuario.tentativas = 0;
    }
    salvarUsuarios(lista);
  }
  // Mensagem genérica: não revela se o e-mail existe
  avisar("E-mail ou senha incorretos.");
  mostrarAvisos();
  document.getElementById("login_password").value = "";
});

// ---------------------------------------------------------------------------
// Login social (na demonstração só explica, pois exige servidor)
// ---------------------------------------------------------------------------

document.querySelectorAll("button[data-provedor]").forEach((botao) => {
  botao.addEventListener("click", () => {
    avisar(
      `O login com ${botao.dataset.provedor} usa OAuth 2.0 e precisa do servidor Python ` +
      "da versão completa (veja o repositório). Nesta demonstração, use e-mail e senha."
    );
    mostrarAvisos();
  });
});

// ---------------------------------------------------------------------------
// Painel do usuário
// ---------------------------------------------------------------------------

const formatarData = (iso, comHora) => {
  const d = new Date(iso);
  const data = d.toLocaleDateString("pt-BR");
  return comHora
    ? `${data} às ${d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}`
    : data;
};

function preencherPainel(u) {
  const foto = document.getElementById("p-foto");
  const iniciais = document.getElementById("p-iniciais");
  if (u.avatar) {
    foto.src = u.avatar;
    foto.hidden = false;
    iniciais.hidden = true;
  } else {
    iniciais.textContent = (u.nome[0] + (u.sobrenome[0] || "")).toUpperCase();
    iniciais.hidden = false;
    foto.hidden = true;
  }
  document.getElementById("p-ola").textContent = `Olá, ${u.nome}!`;
  document.getElementById("p-email").textContent = u.email;
  document.getElementById("p-nome").textContent = `${u.nome} ${u.sobrenome}`.trim();
  document.getElementById("p-criado").textContent = formatarData(u.criadoEm);
  document.getElementById("p-acesso").textContent = formatarData(u.ultimoAcesso, true);
}

document.getElementById("btn-sair").addEventListener("click", () => {
  apagar(CHAVE_SESSAO);
  avisar("Você saiu da sua conta.", "sucesso");
  ir("login");
});

// Inicia
navegar();
