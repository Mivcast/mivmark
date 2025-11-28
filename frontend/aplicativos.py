import streamlit as st
import httpx
from verificar_acesso import usuario_tem_acesso

API_URL = "https://mivmark-backend.onrender.com"

def get_headers():
    token = st.session_state.get("token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}

def tela_aplicativos():
    st.title("📱 Aplicativos Disponíveis")

    if "token" not in st.session_state or not st.session_state.token:
        st.warning("⚠️ Você precisa estar logado para visualizar os aplicativos.")
        return

    try:
        response = httpx.get(f"{API_URL}/aplicativos/admin/listar_todos", headers=get_headers())
        if response.status_code != 200:
            st.error(f"Erro na resposta da API ({response.status_code})")
            st.text(response.text)
            return

        apps = response.json()
    except Exception as e:
        st.error(f"Erro ao buscar aplicativos: {e}")
        return

    colunas = st.columns(4)
    for idx, app in enumerate(apps):
        col = colunas[idx % 4]
        with col:
            icone = app.get("icone_url") or "https://via.placeholder.com/150"
            st.image(icone, use_container_width=True)
            st.markdown(f"### {app.get('titulo', 'Sem Título')}")
            st.caption(app.get("descricao", "")[:80] + "...")
            preco = app.get("preco", 0)
            if app.get("gratuito", True):
                st.markdown("🟢 Gratuito")
            else:
                st.markdown(f"💰 R$ {preco:.2f}")

            if app.get("gratuito", True) or app.get("id") in st.session_state.get("apps_liberados", []):
                if st.button("▶️ Acessar", key=f"acessar_{app['id']}"):
                    st.session_state["app_liberado"] = app["id"]
                    st.rerun()
            else:
                if st.button("💳 Comprar", key=f"comprar_{app['id']}"):
                    st.session_state["app_checkout"] = app["id"]
                    st.rerun()

def listar_aplicativos_admin():
    st.markdown("### ➕ Adicionar Novo Aplicativo")

    with st.form("form_add_app", clear_on_submit=True):
        titulo = st.text_input("Título do App")
        descricao = st.text_area("Descrição")
        icone_url = st.text_input("URL do Ícone")
        categoria = st.text_input("Categoria")
        gratuito = st.checkbox("Gratuito", value=True)
        preco = st.number_input("Preço (R$)", min_value=0.0, step=0.5, value=0.0)
        destaque = st.checkbox("Destaque")
        ativo = st.checkbox("Ativo", value=True)

        submitted = st.form_submit_button("Salvar Aplicativo")
        if submitted:
            payload = {
                "titulo": titulo,
                "descricao": descricao,
                "icone_url": icone_url,
                "categoria": categoria,
                "gratuito": gratuito,
                "preco": preco,
                "destaque": destaque,
                "ativo": ativo
            }

            try:
                response = httpx.post(
                    f"{API_URL}/aplicativos/admin/adicionar_app",
                    json=payload,
                    headers=get_headers()
                )
                if response.status_code == 200:
                    st.success("✅ Aplicativo adicionado com sucesso!")
                    st.rerun()
                else:
                    st.error(f"Erro ao adicionar aplicativo: {response.status_code}")
                    st.text(response.text)
            except Exception as e:
                st.error(f"Erro inesperado: {e}")

    st.divider()
    st.markdown("### 🗂 Aplicativos Existentes")

    try:
        response = httpx.get(f"{API_URL}/aplicativos/admin/listar_todos", headers=get_headers())
        if response.status_code == 200:
            apps = response.json()
            for app in apps:
                with st.expander(f"📱 {app['titulo']}"):
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        icone = app.get("icone_url") or "https://via.placeholder.com/150"
                        st.image(icone, width=100)
                    with col2:
                        st.markdown(f"**Descrição:** {app.get('descricao', '')}")
                        st.markdown(f"**Categoria:** {app.get('categoria', 'N/A')}")
                        st.markdown(f"**Preço:** {'Gratuito' if app.get('gratuito') else f'R$ {app.get('preco', 0):.2f}'}")
                        st.markdown(f"**Destaque:** {'✅' if app.get('destaque') else '❌'}")
                        st.markdown(f"**Ativo:** {'🟢 Sim' if app.get('ativo') else '🔴 Não'}")
                        st.markdown(f"**Criado em:** {app.get('criado_em', '')}")

                    st.markdown("### ✏️ Editar Aplicativo")
                    with st.form(f"form_editar_{app['id']}"):
                        titulo = st.text_input("Título", value=app["titulo"])
                        descricao = st.text_area("Descrição", value=app["descricao"])
                        icone_url = st.text_input("URL do Ícone", value=app["icone_url"])
                        categoria = st.text_input("Categoria", value=app["categoria"])
                        gratuito = st.checkbox("Gratuito", value=app["gratuito"])
                        preco = st.number_input("Preço", value=app["preco"], step=0.5)
                        destaque = st.checkbox("Destaque", value=app["destaque"])
                        ativo = st.checkbox("Ativo", value=app["ativo"])
                        submit_editar = st.form_submit_button("💾 Salvar Alterações")

                        if submit_editar:
                            payload = {
                                "titulo": titulo,
                                "descricao": descricao,
                                "icone_url": icone_url,
                                "categoria": categoria,
                                "gratuito": gratuito,
                                "preco": preco,
                                "destaque": destaque,
                                "ativo": ativo
                            }

                            try:
                                resp = httpx.put(f"{API_URL}/aplicativos/{app['id']}", json=payload, headers=get_headers())
                                if resp.status_code == 200:
                                    st.success("✅ Aplicativo atualizado com sucesso!")
                                    st.rerun()
                                else:
                                    st.error(f"Erro ao atualizar: {resp.status_code}")
                            except Exception as e:
                                st.error(f"Erro ao editar: {e}")

                    st.markdown("---")
                    if st.button("🗑 Excluir", key=f"excluir_{app['id']}"):
                        try:
                            delete = delete = httpx.delete(f"{API_URL}/aplicativos/{app['id']}", headers=get_headers())
                            if delete.status_code == 200:
                                st.success("Aplicativo excluído com sucesso!")
                                st.rerun()
                            else:
                                st.error(f"Erro ao excluir aplicativo: {delete.status_code}")
                                st.text(delete.text)
                        except Exception as e:
                            st.error(f"Erro ao excluir: {e}")
        else:
            st.error(f"Erro ao buscar aplicativos: {response.status_code}")
            st.text(response.text)
    except Exception as e:
        st.error(f"Erro ao buscar aplicativos: {e}")


