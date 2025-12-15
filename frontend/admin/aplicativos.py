import streamlit as st
import httpx
from datetime import datetime

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").strip().rstrip("/")

def painel_admin_aplicativos():
    st.subheader("🛠️ Painel de Aplicativos")

    # Seção: Adicionar ou editar aplicativo
    with st.expander("➕ Cadastrar Novo Aplicativo ou Editar Existente"):
        app_id = st.text_input("ID do App (deixe em branco para criar novo)", "")
        titulo = st.text_input("Título")
        descricao = st.text_area("Descrição")
        icone_url = st.text_input("URL do Ícone", "https://via.placeholder.com/150")
        categoria = st.text_input("Categoria")
        gratuito = st.checkbox("Gratuito", value=True)
        preco = st.number_input("Preço (R$)", min_value=0.0, format="%.2f")
        destaque = st.checkbox("Destaque", value=False)
        ativo = st.checkbox("Ativo", value=True)

        if st.button("Salvar App"):
            dados = {
                "titulo": titulo,
                "descricao": descricao,
                "icone_url": icone_url,
                "categoria": categoria,
                "gratuito": gratuito,
                "preco": preco,
                "destaque": destaque,
                "ativo": ativo,
            }
            try:
                if app_id:
                    r = httpx.put(f"{API_URL}/aplicativos/{app_id}", json=dados)
                else:
                    r = httpx.post(f"{API_URL}/aplicativos", json=dados)

                if r.status_code in [200, 201]:
                    st.success("Aplicativo salvo com sucesso!")
                    st.rerun()
                else:
                    st.error(f"Erro ao salvar: {r.text}")
            except Exception as e:
                st.error(f"Erro na requisição: {e}")

    st.divider()

    # Seção: Lista de aplicativos existentes
    st.markdown("### 🔹 Aplicativos Cadastrados")
    try:
        resposta = httpx.get(f"{API_URL}/aplicativos")
        if resposta.status_code == 200:
            apps = resposta.json()
            for app in apps:
                with st.container():
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col1:
                        st.image(app["icone_url"], width=80)
                    with col2:
                        st.markdown(f"**{app['titulo']}**")
                        st.caption(app["descricao"][:80] + "...")
                        st.markdown(f"Categoria: {app['categoria']}")
                        st.markdown(f"Preço: {'Gratuito' if app['gratuito'] else f'R$ {app['preco']:.2f}'}")
                        st.markdown(f"ID: `{app['id']}` | {'Ativo' if app['ativo'] else 'Inativo'}")
                    with col3:
                        if st.button("✏️ Editar", key=f"editar_{app['id']}"):
                            st.session_state["editar_app"] = app
                            st.rerun()
                        if st.button("🗑 Excluir", key=f"excluir_{app['id']}"):
                            httpx.delete(f"{API_URL}/aplicativos/{app['id']}")
                            st.success("App excluído")
                            st.rerun()
        else:
            st.warning("Não foi possível buscar os aplicativos")
    except Exception as e:
        st.error(f"Erro ao carregar aplicativos: {e}")

    # Se vier do editar
    if "editar_app" in st.session_state:
        app = st.session_state.pop("editar_app")
        st.experimental_set_query_params(
            titulo=app["titulo"],
            descricao=app["descricao"],
            icone_url=app["icone_url"],
            categoria=app["categoria"],
            gratuito=app["gratuito"],
            preco=app["preco"],
            destaque=app["destaque"],
            ativo=app["ativo"],
            app_id=app["id"]
        )
