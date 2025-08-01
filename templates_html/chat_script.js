const botaoChat = document.createElement("button");
botaoChat.innerText = "💬 Ajuda";
botaoChat.style = "background:#0077cc;color:white;padding:10px 18px;border:none;border-radius:6px;position:fixed;bottom:20px;right:20px;cursor:pointer;z-index:9999";
document.body.appendChild(botaoChat);

const caixa = document.createElement("div");
caixa.style = "position:fixed;bottom:70px;right:20px;width:300px;background:white;border:1px solid #ccc;border-radius:8px;padding:10px;display:none;z-index:9999;";
document.body.appendChild(caixa);

const historico = document.createElement("div");
historico.style = "height:200px;overflow-y:auto;font-size:14px;margin-bottom:10px";
caixa.appendChild(historico);

const input = document.createElement("input");
input.type = "text";
input.placeholder = "Digite sua pergunta...";
input.style = "width:100%;padding:8px;";
caixa.appendChild(input);

input.addEventListener("keydown", async function (e) {
  if (e.key === "Enter" && input.value.trim()) {
    historico.innerHTML += `<p><strong>Você:</strong> ${input.value}</p>`;
    historico.scrollTop = historico.scrollHeight;
    const pergunta = input.value;
    input.value = "...";

    const resp = await fetch("https://seusite.com.br/mark/responder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mensagem: pergunta, usuario_id: usuario_id })
    });
    const json = await resp.json();
    historico.innerHTML += `<p><strong>MARK:</strong> ${json.resposta}</p>`;
    historico.scrollTop = historico.scrollHeight;
    input.value = "";
  }
});

botaoChat.onclick = () => {
  caixa.style.display = caixa.style.display === "none" ? "block" : "none";
};
