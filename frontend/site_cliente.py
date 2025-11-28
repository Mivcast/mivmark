import streamlit as st
import httpx
import sys
import os

# Gambiarra saudável pra conseguir importar verificar_acesso
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from verificar_acesso import usuario_tem_acesso

API_URL = "https://mivmark-backend.onrender.com"

# 🌐 URL base onde os sites gerados serão publicados na internet
# Quando você subir o sistema, ajuste a variável de ambiente PUBLIC_SITE_BASE_URL
# Exemplo: https://app.mivmark.com/sites_gerados
PUBLIC_SITE_BASE_URL = os.getenv(
    "PUBLIC_SITE_BASE_URL",
    "https://seusite.com.br/sites_gerados"  # ajuste depois para o domínio real
)


def tela_site_cliente():
    # ⚠️ Verificação de acesso: Admin sempre tem acesso total
    email_usuario = st.session_state.get("dados_usuario", {}).get("email", "")
    if email_usuario != "matheus@email.com":
        if not usuario_tem_acesso("site"):
            st.warning("⚠️ Este módulo está disponível apenas para planos pagos.")
            st.stop()

    st.title("🌐 Página e Chat do Cliente")

    # Dados do usuário logado
    usuario_id = st.session_state.dados_usuario.get("id")
    nome_empresa = st.session_state.dados_usuario.get("nome_empresa", "").replace(" ", "_")
    nome_arquivo = f"{nome_empresa}.html"

    # 🔗 Link público do site (na internet) – configurável pela PUBLIC_SITE_BASE_URL
    link_site = f"{PUBLIC_SITE_BASE_URL}/{nome_arquivo}"

    # ✅ Bloco explicativo do MARK com visual amigável
    st.markdown(
        f"""
    <div style="background:#e8f4ff;padding:20px;border-left:5px solid #007bff;border-radius:10px;margin-bottom:20px">
        <h4>🎉 Parabéns! Seu site foi criado automaticamente</h4>
        <p>
            O site foi gerado com todos os dados preenchidos na aba
            <a href="?page=empresa"><strong>Empresa</strong></a>.
            Caso você veja algo no site que queira ajustar, entre na aba <strong>Empresa</strong>,
            edite as informações por lá e gere o site novamente: o conteúdo será atualizado automaticamente.
        </p>
        <p>Você pode visualizar seu site clicando no link abaixo:</p>
        <a href="{link_site}" target="_blank"><strong>🔗 {link_site}</strong></a><br><br>
        <p>🧠 Quanto mais informações você preencher na aba <strong>Empresa</strong>, mais completo seu site será!</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("## 🧠 Informações adicionais para o MARK")
    st.write(
        "Esse campo serve para você passar mensagens específicas que o seu cliente verá no chat dentro do site. Use com sabedoria!"
    )

    info = st.text_area("📌 Escreva aqui as informações adicionais para o MARK", height=150)

    if st.button("💾 Regerar Site com essas informações"):
        payload = {
            "usuario_id": usuario_id,
            "bio": "",
            "agendamento_ativo": False,
            "horarios_disponiveis": [],
            "informacoes_adicionais": info,
        }
        try:
            r = httpx.post(f"{API_URL}/site-cliente/gerar", json=payload)
            if r.status_code == 200:
                st.success("✅ Site atualizado com sucesso!")
                st.markdown(
                    f"🔗 [Visualizar site atualizado]({link_site})",
                    unsafe_allow_html=True,
                )
            else:
                st.error(f"Erro: {r.text}")
        except Exception as e:
            st.error(f"Erro ao gerar site: {e}")
