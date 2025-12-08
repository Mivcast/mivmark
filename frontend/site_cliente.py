# frontend/site_cliente.py
import os
import httpx
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")


def tela_site_cliente():
    # 🧠 Tenta usar o último arquivo gerado para montar o link de exemplo
    arquivo_exemplo = st.session_state.get("ultimo_site_arquivo")
    if arquivo_exemplo:
        link_exemplo = f"https://mivmark-frontend.onrender.com/{arquivo_exemplo}"
    else:
        link_exemplo = "https://mivmark-frontend.onrender.com/NOME_DA_SUA_EMPRESA.html"

    usuario = st.session_state.get("dados_usuario", {}) or {}
    usuario_id = usuario.get("id")

    if not usuario_id:
        st.warning("Não foi possível identificar o usuário logado. Faça login novamente.")
        return

    # 🔹 Texto de introdução (agora usando o link_exemplo real)
    st.markdown(
        f"""
    # 🌐 Página e Chat do Cliente

    Parabéns! 🎉  
    O seu **site exclusivo** foi criado com base nos dados cadastrados na aba **Empresa**.

    Assim que você gerar o site, ele ficará disponível em um link como:

    👉 **{link_exemplo}**

    Você poderá **copiar esse link** e usar em:
    - Bio do Instagram  
    - WhatsApp Business  
    - Google Meu Negócio  
    - QR Code  
    - Cartões digitais  
    - Onde você quiser divulgar seu negócio!

    ---

    ### 🤖 Chat Inteligente Integrado

    Seu site também vem com um **Atendente Virtual Inteligente**, totalmente integrado ao seu negócio.  
    Ele recebe automaticamente as informações da sua empresa e responde seus clientes com:
    - Explicações sobre seus serviços  
    - Horários  
    - Endereço  
    - Informações adicionais que você cadastrar aqui  
    - Mensagens personalizadas

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

        st.success("Site gerado com sucesso! ✅")

        # Se o backend já montou URL pública (quando você configurar SITES_BASE_URL no Render)
        if url:
            st.markdown(f"🔗 **Seu site está no ar:** [{url}]({url})")

        # Se ainda não tem URL pública, montamos o link no formato que você quer
        elif arquivo:
            link_front = f"https://mivmark-frontend.onrender.com/{arquivo}"
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
