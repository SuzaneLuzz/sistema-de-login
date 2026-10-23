// Mostrar / esconder senha
document.querySelectorAll(".olho").forEach((botao) => {
  botao.addEventListener("click", () => {
    const campo = document.getElementById(botao.dataset.alvo);
    const mostrar = campo.type === "password";
    campo.type = mostrar ? "text" : "password";
    botao.classList.toggle("visivel", mostrar);
    botao.setAttribute("aria-label", mostrar ? "Esconder senha" : "Mostrar senha");
  });
});

// Checklist de força da senha (só na tela de cadastro)
const senha = document.getElementById("password");
const confirmar = document.getElementById("confirm_password");
const regras = document.getElementById("regras-senha");
const aviso = document.getElementById("senhas-diferentes");

const testes = {
  tamanho: (s) => s.length >= 8,
  maiuscula: (s) => /[A-Z]/.test(s),
  minuscula: (s) => /[a-z]/.test(s),
  numero: (s) => /\d/.test(s),
};

const barra = document.getElementById("forca-preenchimento");
const coresForca = ["#e0475b", "#e0475b", "#f0a33a", "#e8c53a", "#15a36b"];

function atualizarRegras() {
  if (!regras) return;
  let cumpridas = 0;
  regras.querySelectorAll("li").forEach((li) => {
    const ok = testes[li.dataset.regra](senha.value);
    li.classList.toggle("ok", ok);
    if (ok) cumpridas++;
  });
  if (barra) {
    barra.style.width = senha.value ? `${cumpridas * 25}%` : "0";
    barra.style.background = coresForca[cumpridas];
  }
}

function conferirIguais() {
  if (!aviso) return;
  aviso.hidden = !confirmar.value || confirmar.value === senha.value;
}

if (senha && regras) {
  senha.addEventListener("input", () => { atualizarRegras(); conferirIguais(); });
  confirmar.addEventListener("input", conferirIguais);
}

// Upload de foto de perfil com pré-visualização
const arquivo = document.getElementById("avatar_file");
if (arquivo) {
  const opcaoUpload = document.querySelector(".avatar-upload");
  const radioUpload = opcaoUpload.querySelector('input[type="radio"]');
  const preview = document.getElementById("preview-upload");

  opcaoUpload.addEventListener("click", (evento) => {
    if (evento.target !== arquivo) {
      evento.preventDefault();
      arquivo.click();
    }
  });

  arquivo.addEventListener("change", () => {
    const foto = arquivo.files[0];
    if (!foto) return;
    if (foto.size > 2 * 1024 * 1024) {
      alert("A imagem deve ter no máximo 2 MB.");
      arquivo.value = "";
      return;
    }
    const leitor = new FileReader();
    leitor.onload = () => {
      preview.style.backgroundImage = `url(${leitor.result})`;
      opcaoUpload.classList.add("com-foto");
      radioUpload.checked = true;
    };
    leitor.readAsDataURL(foto);
  });
}
