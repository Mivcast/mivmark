# frontend/admin/planos.py
import os
import httpx
import streamlit as st

API_URL = os.getenv("API_URL", "").strip().rstrip("/")

# ✅ Local: se não existir env var, usa localhost
if not API_URL:
    API_URL = "http://127.0.0.1:8000"


# ============================================================
# ✅ Catálogo oficial de módulos (padronize e use só estes slugs)
# ============================================================
MODULOS_CATALOGO = [
    ("empresa", "🏢 Empresa"),
    ("saude", "❤️ Saúde da Empresa"),
    ("consultoria", "📋 Consultoria"),
    ("cursos", "🎓 Cursos"),
    ("aplicativos", "📱 Aplicativos"),
    ("orcamento", "💰 Orçamento"),
    ("agenda", "📅 Agenda"),
    ("consultor_mensal", "📣 Consultor Mensal"),
    ("arquivo", "📁 Arquivos"),
    ("mark", "🤖 MARK IA"),
    ("site_chat", "🌐 Site e Chat"),
]

MODULOS_SLUGS = [m[0] for m in MODULOS_CATALOGO]
MODULOS_LABEL = {slug: label for slug, label in MODULOS_CATALOGO}

# Aliases comuns (para não quebrar planos antigos)
ALIASES = {
    "arquivos": "arquivo",
    "chat": "mark",
    "mark_ia": "mark",
    "site": "site_chat",
    "site_e_chat": "site_chat",
    "consultor": "consultor_mensal",
    "consultor-mensal": "consultor_mensal",
}


def normalizar_modulos(modulos):
    """
    Recebe lista ou string e devolve lista padronizada:
    - aplica aliases
    - remove espaços
    - remove vazios
    - mantém apenas módulos do catálogo
    """
    if modulos is None:
        return []

    if isinstance(modulos, str):
        itens = [x.strip() for x in modulos.split(",")]
    else:
        itens = [str(x).strip() for x in modulos]

    out = []
    for m in itens:
        if not m:
            continue
        m = ALIASES.get(m, m)
        if m in MODULOS_SLUGS and m not in out:
            out.append(m)

    return out


def aba_gerenciar_planos():
    st.subheader("🧩 Gerenciar Planos do Sistema")

    # ------------------------
    # Carrega planos
    # ------------------------
    try:
        resposta = httpx.get(f"{API_URL}/planos/", timeout=20)
        if resposta.status_code != 200:
            st.error(f"Erro ao buscar planos. Status: {resposta.status_code}")
            st.text(resposta.text)
            return
        planos = resposta.json() or []
    except Exception as e:
        st.error(f"Erro ao carregar planos: {e}")
        return

    # =========================================================
    # ➕ Criar novo plano
    # =========================================================
    st.markdown("### ➕ Adicionar Novo Plano")

    with st.form("novo_plano", clear_on_submit=False):
        nome = st.text_input("Nome do Plano")
        descricao = st.text_area("Descrição")
        preco_mensal = st.number_input("Preço Mensal", step=1.0, min_value=0.0)
        preco_anual = st.number_input("Preço Anual", step=1.0, min_value=0.0)

        # ✅ Multiselect com labels humanizadas
        modulos_selecionados = st.multiselect(
            "Módulos Liberados",
            options=MODULOS_SLUGS,
            format_func=lambda x: f"{MODULOS_LABEL.get(x, x)}  ({x})",
            default=[]
        )

        bonus = st.text_area("Bônus / Extras (opcional)")
        ativo = st.checkbox("Ativo", value=True)
        enviar = st.form_submit_button("Salvar")

        if enviar:
            if not nome.strip():
                st.warning("Informe o nome do plano.")
                st.stop()

            payload = {
                "nome": nome.strip(),
                "descricao": descricao.strip() if descricao else "",
                "preco_mensal": float(preco_mensal),
                "preco_anual": float(preco_anual),
                "modulos_liberados": normalizar_modulos(modulos_selecionados),
                "bonus": bonus.strip() if bonus else "",
                "ativo": bool(ativo),
            }

            try:
                r = httpx.post(f"{API_URL}/planos/", json=payload, timeout=30)
                if r.status_code == 200:
                    st.success("✅ Plano cadastrado com sucesso!")
                    st.rerun()
                else:
                    st.error(f"Erro ao salvar plano (status {r.status_code}).")
                    st.text(r.text)
            except Exception as e:
                st.error(f"Falha ao salvar plano: {e}")

    st.divider()

    # =========================================================
    # 📋 Editar planos existentes
    # =========================================================
    st.markdown("### 📋 Planos Existentes")

    if not planos:
        st.info("Nenhum plano cadastrado.")
        return

    for plano in planos:
        plano_id = plano.get("id")
        nome_plano = plano.get("nome", "Sem nome")
        preco = plano.get("preco_mensal", 0.0)

        # Normaliza módulos que vieram do backend (pode conter 'arquivos', 'chat', etc.)
        modulos_atuais = normalizar_modulos(plano.get("modulos_liberados") or [])

        with st.expander(f"📦 {nome_plano} - R$ {float(preco):.2f}/mês", expanded=False):
            nome = st.text_input("Nome", nome_plano, key=f"n_{plano_id}")
            descricao = st.text_area("Descrição", plano.get("descricao", ""), key=f"d_{plano_id}")
            mensal = st.number_input("Mensal", value=float(plano.get("preco_mensal", 0.0)), key=f"m_{plano_id}")
            anual = st.number_input("Anual", value=float(plano.get("preco_anual", 0.0)), key=f"a_{plano_id}")

            modulos_edit = st.multiselect(
                "Módulos Liberados",
                options=MODULOS_SLUGS,
                format_func=lambda x: f"{MODULOS_LABEL.get(x, x)}  ({x})",
                default=modulos_atuais,
                key=f"mods_{plano_id}"
            )

            bonus = st.text_area("Bônus", plano.get("bonus", ""), key=f"b_{plano_id}")
            ativo = st.checkbox("Ativo", bool(plano.get("ativo", True)), key=f"act_{plano_id}")

            st.caption("Slugs selecionados: " + ", ".join(normalizar_modulos(modulos_edit)))

            col1, col2 = st.columns(2)

            with col1:
                if st.button("💾 Atualizar", key=f"up_{plano_id}"):
                    payload = {
                        "nome": nome.strip(),
                        "descricao": descricao.strip() if descricao else "",
                        "preco_mensal": float(mensal),
                        "preco_anual": float(anual),
                        "modulos_liberados": normalizar_modulos(modulos_edit),
                        "bonus": bonus.strip() if bonus else "",
                        "ativo": bool(ativo),
                    }

                    try:
                        r = httpx.put(f"{API_URL}/planos/{plano_id}", json=payload, timeout=30)
                        if r.status_code == 200:
                            st.success("✅ Atualizado com sucesso!")
                            st.rerun()
                        else:
                            st.error(f"Erro ao atualizar (status {r.status_code}).")
                            st.text(r.text)
                    except Exception as e:
                        st.error(f"Falha ao atualizar plano: {e}")

            with col2:
                if st.button("🗑 Excluir", key=f"del_{plano_id}"):
                    try:
                        r = httpx.delete(f"{API_URL}/planos/{plano_id}", timeout=30)
                        if r.status_code == 200:
                            st.success("🗑 Plano excluído.")
                            st.rerun()
                        else:
                            st.error(f"Erro ao excluir (status {r.status_code}).")
                            st.text(r.text)
                    except Exception as e:
                        st.error(f"Falha ao excluir plano: {e}")
