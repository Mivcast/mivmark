import streamlit as st
import httpx
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from verificar_acesso import usuario_tem_acesso


API_URL = "https://mivmark-backend.onrender.com"

def tela_site_cliente():
    # ⚠️ Verificação de acesso: Admin sempre tem acesso total
    email_usuario = st.session_state.get("dados_usuario", {}).get("email", "")
    if email_usuario != "matheus@email.com":
        if not usuario_tem_acesso("site"):
            st.warning("⚠️ Este módulo está disponível apenas para planos pagos.")
            st.stop()
    st.title("🌐 Página e Chat do Cliente")

    usuario_id = st.session_state.dados_usuario.get("id")
    nome_empresa = st.session_state.dados_usuario.get("nome_empresa", "").replace(" ", "_")
    link_site = f"data/sites_gerados/{nome_empresa}.html"

    # ✅ Bloco explicativo do MARK com visual amigável
    st.markdown(f"""
    <div style="background:#e8f4ff;padding:20px;border-left:5px solid #007bff;border-radius:10px;margin-bottom:20px">
        <h4>🎉 Parabéns! Seu site foi criado automaticamente</h4>
        <p>O site foi gerado com todos os dados preenchidos na aba <a href="?page=empresa"><strong>Dados da Empresa</strong></a>.</p>
        <p>Você pode visualizar seu site clicando no link abaixo:</p>
        <a href="{link_site}" target="_blank"><strong>🔗 {link_site}</strong></a><br><br>
        <p>🧠 Quanto mais informações você preencher nos Dados da Empresa, mais completo seu site será!</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("## 🧠 Informações adicionais para o MARK")
    st.write("Esse campo serve para você passar mensagens específicas que o seu cliente verá no chat dentro do site. Use com sabedoria!")

    info = st.text_area("📌 Escreva aqui as informações adicionais para o MARK", height=150)

    if st.button("💾 Regerar Site com essas informações"):
        payload = {
            "usuario_id": usuario_id,
            "bio": "",
            "agendamento_ativo": False,
            "horarios_disponiveis": [],
            "informacoes_adicionais": info
        }
        try:
            r = httpx.post(f"{API_URL}/site-cliente/gerar", json=payload)
            if r.status_code == 200:
                st.success("✅ Site atualizado com sucesso!")
                st.markdown(f"🔗 [Visualizar site atualizado]({link_site})", unsafe_allow_html=True)
            else:
                st.error(f"Erro: {r.text}")
        except Exception as e:
            st.error(f"Erro ao gerar site: {e}")
