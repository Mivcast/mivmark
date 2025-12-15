# Adicione esta aba no seu painel_admin()
import os
import httpx
import streamlit as st

API_URL = os.getenv("API_URL")

if not API_URL:
    st.error("❌ API_URL não configurada no ambiente.")
    st.stop()

API_URL = API_URL.strip().rstrip("/")




def aba_gerenciar_planos():
    st.subheader("🧩 Gerenciar Planos do Sistema")


    try:
        resposta = httpx.get(f"{API_URL}/planos/")
        if resposta.status_code != 200:
            st.error("Erro ao buscar planos.")
            return
        planos = resposta.json()
    except Exception as e:
        st.error(f"Erro ao carregar planos: {e}")
        return

    st.markdown("### ➕ Adicionar Novo Plano")
    with st.form("novo_plano"):
        nome = st.text_input("Nome do Plano")
        descricao = st.text_area("Descrição")
        preco_mensal = st.number_input("Preço Mensal", step=1.0)
        preco_anual = st.number_input("Preço Anual", step=1.0)
        modulos = st.multiselect("Módulos Liberados", [
            "empresa", "saude", "orcamento", "aplicativos", "marketing",
            "branding", "chat", "consultoria", "cursos", "arquivos",
            "agenda", "historico"
        ])
        bonus = st.text_area("Bônus / Extras (opcional)")
        ativo = st.checkbox("Ativo", value=True)
        enviar = st.form_submit_button("Salvar")

        if enviar:
            payload = {
                "nome": nome,
                "descricao": descricao,
                "preco_mensal": preco_mensal,
                "preco_anual": preco_anual,
                "modulos_liberados": modulos,
                "bonus": bonus,
                "ativo": ativo
            }
            r = httpx.post(f"{API_URL}/planos/", json=payload)
            if r.status_code == 200:
                st.success("✅ Plano cadastrado com sucesso!")
                st.rerun()
            else:
                st.error("Erro ao salvar plano")

    st.divider()
    st.markdown("### 📋 Planos Existentes")

    for plano in planos:
        with st.expander(f"📦 {plano['nome']} - R$ {plano['preco_mensal']:.2f}/mês"):
            nome = st.text_input("Nome", plano['nome'], key=f"n_{plano['id']}")
            descricao = st.text_area("Descrição", plano.get('descricao', ''), key=f"d_{plano['id']}")
            mensal = st.number_input("Mensal", value=plano['preco_mensal'], key=f"m_{plano['id']}")
            anual = st.number_input("Anual", value=plano['preco_anual'], key=f"a_{plano['id']}")
            modulos = st.text_area("Módulos Liberados", ", ".join(plano['modulos_liberados']), key=f"mod_{plano['id']}")
            bonus = st.text_area("Bônus", plano.get('bonus', ''), key=f"b_{plano['id']}")
            ativo = st.checkbox("Ativo", plano['ativo'], key=f"act_{plano['id']}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Atualizar", key=f"up_{plano['id']}"):
                    payload = {
                        "nome": nome,
                        "descricao": descricao,
                        "preco_mensal": mensal,
                        "preco_anual": anual,
                        "modulos_liberados": [m.strip() for m in modulos.split(",")],
                        "bonus": bonus,
                        "ativo": ativo
                    }
                    r = httpx.put(f"{API_URL}/planos/{plano['id']}", json=payload)
                    st.write("DEBUG resposta:", r.status_code, r.text)
                    if r.status_code == 200:
                        st.success("Atualizado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Erro ao atualizar")

            with col2:
                if st.button("🗑 Excluir", key=f"del_{plano['id']}"):
                    r = httpx.delete(f"{API_URL}/planos/{plano['id']}")
                    if r.status_code == 200:
                        st.success("Plano excluído.")
                        st.rerun()
                    else:
                        st.error("Erro ao excluir plano")