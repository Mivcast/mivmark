# frontend/site_cliente.py
import os
import httpx
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# Base pública dos sites gerados (normalmente o backend)
SITES_BASE_URL = os.getenv("SITES_BASE_URL", f"{API_URL}/sites")


def tela_site_cliente():
    st.title("🌐 Página e Chat do Cliente")

    # 🧠 Tenta usar o último arquivo gerado para montar o link de exemplo
    arquivo_exemplo = st.session_state.get("ultimo_site_arquivo")
    if arquivo_exemplo:
        link_exemplo = f"{SITES_BASE_URL}/{arquivo_exemplo}"
    else:
        link_exemplo = f"{SITES_BASE_URL}/NOME_DA_SUA_EMPRESA.html"

    # Dados do usuário logado (para identificar o "dono" do site/chat)
    usuario = st.session_state.get("dados_usuario", {}) or {}
    usuario_id = usuario.get("id")

    if not usuario_id:
        st.warning("Não foi possível identificar o usuário logado. Faça login novamente.")
        return

    # 🔹 Texto de introdução (usando o link_exemplo apenas como referência visual)
    st.markdown(
        f"""
    
    ## Parabéns! Você Ganhou um Site com Chat Inteligente 🎉 

    ### 🌐 Site + Chat Inteligente Integrado
 
    🚀 Você acaba de ganhar um **Site exclusivo** que será criado com base nos dados cadastrados na aba **Empresa**.

    No final desta página terá o botão para **Gerar o Site** 👇🏼
    
    🎯 Você poderá usar o site para divulgar seu negócio onde quiser:
    ▪️ Bio do Instagram  
    ▪️ WhatsApp Business  
    ▪️ Google Meu Negócio  
    ▪️ QR Code  
    ▪️ Cartões digitais, etc.

    Exemplo de link do seu site (quando estiver publicado):  
    `{link_exemplo}`

    ---

    ### 🤖 Chat Inteligente Integrado

    🚀 Seu site vem com um **Atendente Virtual Inteligente**, totalmente integrado ao seu negócio.  
    🎯 Ele recebe automaticamente as informações da sua empresa e responde seus clientes com:
    ▪️ Explicações sobre seus serviços  
    ▪️ Horários  
    ▪️ Endereço  
    ▪️ Informações adicionais que você cadastrar aqui  
    ▪️ Mensagens personalizadas

    Isso transforma seu site em um **atendimento 24h**, profissional e moderno!

    ---

    ### 📌 Observações importantes

    1. **Deseja usar um domínio próprio?**  
       Você pode comprar o domínio que quiser (ex.: Registro.br) e fazer redirecionamento para o link do seu site.

    2. **Quer personalizar o design ou criar novas seções?**  
       A equipe da **MivCast** pode criar melhorias, páginas adicionais e novas versões do seu site.  
       Basta solicitar um orçamento!

    ---
    """
    )

    st.markdown("---")

    st.subheader("Opções adicionais para o site e para o chat inteligente")

    bio = st.text_area(
        "Mensagem de boas-vindas / Bio para o início do site (opcional):",
        help=(
            "Ex.: 'Seja bem-vindo ao Restaurante do João, aqui você encontra "
            "comida caseira todos os dias...'"
        ),
    )

    info_extra = st.text_area(
        "Informações adicionais para o atendente virtual (chat) (opcional):",
        help="Regras, políticas, detalhes de entrega, prazos, formas de pagamento, etc.",
    )

    col1, col2 = st.columns(2)
    with col1:
        agendamento_ativo = st.checkbox("Ativar agendamento on-line?", value=False)
    with col2:
        horarios_txt = st.text_input(
            "Horários disponíveis (separados por vírgula)",
            placeholder="Ex.: 08h–12h, 14h–18h",
        )

    horarios_disponiveis = [h.strip() for h in horarios_txt.split(",") if h.strip()]

    if st.button("🚀 Gerar / Atualizar site agora", use_container_width=True):
        payload = {
            "usuario_id": usuario_id,
            "bio": bio,
            "agendamento_ativo": agendamento_ativo,
            "horarios_disponiveis": horarios_disponiveis,
            "informacoes_adicionais": info_extra,
        }

        try:
            r = httpx.post(f"{API_URL}/site_cliente/gerar", json=payload, timeout=60.0)
        except Exception as e:
            st.error(f"Erro ao comunicar com o servidor: {e}")
            return

        if r.status_code != 200:
            st.error(f"Erro ao gerar o site: {r.status_code} - {r.text}")
            return

        dados = r.json()
        arquivo = dados.get("arquivo")
        url = dados.get("url_publica")

        # 🧠 Guarda na sessão o último arquivo gerado
        if arquivo:
            st.session_state["ultimo_site_arquivo"] = arquivo
            link_exemplo = f"{SITES_BASE_URL}/{arquivo}"

        st.success("Site gerado com sucesso! ✅")

        # Se o backend já montou URL pública (quando você configurar SITES_BASE_URL no Render)
        if url:
            st.markdown(f"🔗 **Seu site está no ar:** [{url}]({url})")

        # Se ainda não tem URL pública, montamos o link no formato que você quer
        elif arquivo:
            link_front = f"{SITES_BASE_URL}/{arquivo}"
            st.markdown(f"🔗 **Seu site está no ar:** [{link_front}]({link_front})")

        else:
            st.warning(
                "O site foi gerado, mas não foi possível montar a URL pública. "
                "Verifique a variável `SITES_BASE_URL` no backend."
            )

        st.info(
            "Dica: você pode copiar esse link e usar nas redes sociais, WhatsApp, "
            "Google Meu Negócio, etc."
        )

    # ---------------------------------------------
    # 🔹 Outras formas de usar o chat inteligente
    # ---------------------------------------------
    st.markdown("---")
    st.subheader("💬 Formas de usar o seu Chat Inteligente MARK")

    # ID que será usado pelo chat público
    # Aqui usamos o próprio ID do usuário logado como identificador
    chat_id = usuario_id

    # URL base do backend configurada no sistema
    API_BASE = os.getenv("API_URL", "https://mivmark-backend.onrender.com").rstrip("/")

    # URL do site gerado (se já tivemos um arquivo gerado; caso contrário, usamos o link_exemplo)
    url_site = link_exemplo

    # URL do chat público em tela cheia
    url_chat_publico = f"{API_BASE}/mark/chat/{chat_id}"

    # --------------------------------------------------------------------
    # 1) SITE GERADO COM CHAT EMBUTIDO
    # --------------------------------------------------------------------
    st.markdown("### 1️⃣ Site com chat integrado")
    st.markdown(
        f"O seu site com chat integrado ficará disponível neste link (exemplo real ou modelo):\n\n"
        f"`{url_site}`\n\n"
        "Use esse link em:\n"
        "- Bio do Instagram\n"
        "- Botão do WhatsApp Business\n"
        "- Google Meu Negócio\n"
        "- QR Code impresso\n"
        "- Cartões e flyers\n"
    )

    # --------------------------------------------------------------------
    # 2) LINK DIRETO SÓ COM O CHAT
    # --------------------------------------------------------------------
    st.markdown("### 2️⃣ Link direto somente com o Chat (tela cheia)")
    st.markdown(
        f"Este link abre **apenas o chat**, sem o site ao redor:\n\n"
        f"`{url_chat_publico}`\n"
    )
    st.info("Perfeito para Linktree, botão do Instagram, WhatsApp e atendimento rápido.")

    # --------------------------------------------------------------------
    # 3) WIDGET FLUTUANTE PARA QUALQUER SITE
    # --------------------------------------------------------------------
    st.markdown("### 3️⃣ Botão flutuante de chat para colocar no seu site atual")
    st.markdown(
        "Copie o código abaixo e cole antes de `</body>` em qualquer site "
        "(WordPress, Wix, Loja Virtual, HTML etc.):"
    )

    codigo_widget = f"""
<!-- MARK – Botão Flutuante de Chat -->
<script>
  (function() {{
    var chatUrl = "{url_chat_publico}";

    var btn = document.createElement("div");
    btn.id = "mivmark-chat-button";
    btn.innerHTML = "💬 Fale conosco";
    btn.style.position = "fixed";
    btn.style.bottom = "20px";
    btn.style.right = "20px";
    btn.style.zIndex = "99999";
    btn.style.background = "#2563eb";
    btn.style.color = "#ffffff";
    btn.style.borderRadius = "999px";
    btn.style.padding = "10px 16px";
    btn.style.cursor = "pointer";
    btn.style.fontFamily = "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
    btn.style.fontSize = "14px";
    btn.style.boxShadow = "0 10px 25px rgba(15, 23, 42, 0.35)";
    document.body.appendChild(btn);

    var overlay = document.createElement("div");
    overlay.id = "mivmark-chat-overlay";
    overlay.style.position = "fixed";
    overlay.style.top = "0";
    overlay.style.left = "0";
    overlay.style.width = "100%";
    overlay.style.height = "100%";
    overlay.style.background = "rgba(15, 23, 42, 0.65)";
    overlay.style.display = "none";
    overlay.style.zIndex = "99998";

    var iframe = document.createElement("iframe");
    iframe.src = chatUrl;
    iframe.style.position = "absolute";
    iframe.style.bottom = "0";
    iframe.style.right = "0";
    iframe.style.width = "100%";
    iframe.style.maxWidth = "420px";
    iframe.style.height = "80%";
    iframe.style.border = "none";
    iframe.style.borderRadius = "16px 16px 0 0";
    iframe.style.boxShadow = "0 14px 40px rgba(15, 23, 42, 0.45)";
    iframe.style.background = "#ffffff";

    overlay.appendChild(iframe);
    document.body.appendChild(overlay);

    overlay.addEventListener("click", function(e) {{
      if (e.target === overlay) {{
        overlay.style.display = "none";
      }}
    }});

    btn.addEventListener("click", function() {{
      overlay.style.display = "block";
    }});
  }})();
</script>
<!-- Fim MARK -->
"""

    st.code(codigo_widget, language="html")

    st.success("Pronto! Você pode usar seu chat em qualquer lugar usando os links e códigos acima.")
