import streamlit as st
import httpx
import math
import datetime

API_URL = "https://mivmark-backend.onrender.com"


def get_headers():
    token = st.session_state.get("token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


# =========================
# HELPERS
# =========================


def _carregar_curso(curso_id: int):
    try:
        r = httpx.get(f"{API_URL}/cursos/{curso_id}", headers=get_headers())
        if r.status_code != 200:
            st.error("Curso não encontrado.")
            return None
        return r.json()
    except Exception as e:
        st.error(f"Erro ao buscar curso: {e}")
        return None


def _carregar_progresso():
    try:
        r = httpx.get(f"{API_URL}/cursos/progresso", headers=get_headers())
        if r.status_code == 200:
            return r.json().get("aulas_concluidas", [])
    except Exception:
        pass
    return []


def _grade_aulas(aulas, aulas_concluidas, permitir_concluir: bool):
    """
    Mostra as aulas em grade com 3 vídeos por linha.
    """
    if not aulas:
        st.info("Este curso ainda não possui aulas cadastradas.")
        return

    aulas_ordenadas = sorted(aulas, key=lambda a: a.get("ordem") or 0)

    cols = st.columns(3)
    for idx, aula in enumerate(aulas_ordenadas):
        col = cols[idx % 3]
        concluida = aula["id"] in aulas_concluidas

        with col:
            st.markdown(f"#### {aula['titulo']} {'✔️' if concluida else ''}")
            desc = (aula.get("descricao") or "").strip()
            if desc:
                st.caption(desc)
            st.video(aula["video_url"])

            if permitir_concluir:
                if not concluida:
                    if st.button(
                        "✅ Marcar como concluída",
                        key=f"concluir_{aula['id']}",
                    ):
                        try:
                            httpx.post(
                                f"{API_URL}/cursos/aula/{aula['id']}/concluir",
                                headers=get_headers(),
                            )
                            st.success("Aula marcada como concluída!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao marcar aula: {e}")
                else:
                    st.success("✔️ Aula concluída")

        # a cada 3, começa uma nova linha
        if (idx % 3) == 2 and idx != len(aulas_ordenadas) - 1:
            cols = st.columns(3)


# =========================
# TELAS DE DETALHE
# =========================


def _tela_curso_completo(curso_id: int):
    curso = _carregar_curso(curso_id)
    if not curso:
        return

    aulas_concluidas = _carregar_progresso()
    aulas = curso.get("aulas") or []
    total = len(aulas)
    feitas = len([a for a in aulas if a["id"] in aulas_concluidas])
    progresso = feitas / total if total else 0

    st.title(curso["titulo"])
    if curso.get("capa_url"):
        st.image(curso["capa_url"], use_container_width=True)

    st.markdown(f"**Categoria:** {curso.get('categoria') or 'Sem categoria'}")
    st.markdown(curso.get("descricao") or "")

    st.markdown("---")
    st.subheader("📊 Progresso do Curso")
    st.progress(progresso)
    st.caption(
        f"{feitas} de {total} aulas concluídas ({math.floor(progresso * 100) if total else 0}%)"
    )

    st.markdown("---")
    st.subheader("🎥 Aulas do Curso")

    _grade_aulas(aulas, aulas_concluidas, permitir_concluir=True)

    if st.button("⬅️ Voltar para Cursos", key="voltar_curso_completo"):
        st.session_state.pop("curso_liberado", None)
        st.session_state.pop("curso_espiar", None)
        st.session_state.pop("curso_checkout", None)
        st.rerun()


def _tela_curso_preview(curso_id: int):
    """
    Tela de ESPIAR / SAIBA MAIS.
    Mostra descrição, algumas aulas e um CTA para acessar/comprar.
    """
    curso = _carregar_curso(curso_id)
    if not curso:
        return

    aulas = curso.get("aulas") or []

    st.title(curso["titulo"])
    if curso.get("capa_url"):
        st.image(curso["capa_url"], use_container_width=True)

    st.markdown(f"**Categoria:** {curso.get('categoria') or 'Sem categoria'}")
    st.markdown(curso.get("descricao") or "")

    preco = float(curso.get("preco") or 0.0)
    if curso.get("gratuito"):
        st.markdown("🟢 **Curso Gratuito**")
    else:
        preco_pix = preco * 0.9
        st.markdown(f"💰 Valor: **R$ {preco:.2f}**")
        st.markdown(f"⚡ Pix: **R$ {preco_pix:.2f}** • 💳 até 6x sem juros")

    st.markdown("---")
    st.subheader("📚 O que você vai aprender")

    if aulas:
        # mostra só as 3 primeiras aulas como prévia
        previas = sorted(aulas, key=lambda a: a.get("ordem") or 0)[:3]
        for aula in previas:
            st.markdown(f"- **{aula['titulo']}** — {(aula.get('descricao') or '').strip()}")
    else:
        st.caption("As aulas deste curso ainda serão adicionadas em breve.")

    st.markdown("---")
    col1, col2 = st.columns([2, 1])

    with col1:
        if st.button("▶️ Acessar curso completo", key="preview_acessar"):
            st.session_state["curso_liberado"] = curso_id
            st.session_state.pop("curso_espiar", None)
            st.rerun()

    with col2:
        if st.button("⬅️ Voltar para Cursos", key="preview_voltar"):
            st.session_state.pop("curso_espiar", None)
            st.rerun()


# =========================
# LISTAGEM GERAL DE CURSOS
# =========================


def tela_cursos():
    """
    Tela principal do menu 🎓 Cursos.
    Aqui controlamos lista, espiar, acessar e checkout.
    """

    # 1) Se estiver em checkout, mostra checkout
    if st.session_state.get("curso_checkout"):
        tela_checkout(st.session_state["curso_checkout"])
        return

    # 2) Se estiver acessando um curso liberado
    if st.session_state.get("curso_liberado"):
        _tela_curso_completo(st.session_state["curso_liberado"])
        return

    # 3) Se estiver espiando um curso
    if st.session_state.get("curso_espiar"):
        _tela_curso_preview(st.session_state["curso_espiar"])
        return

    # 4) Caso contrário, mostrar grade de cursos
    st.title("🎓 Nossos Cursos")

    try:
        r = httpx.get(f"{API_URL}/cursos/", headers=get_headers())
        if r.status_code != 200:
            st.error("Erro ao carregar cursos.")
            return
        cursos = r.json()
        # Ordenar cursos pela ordem definida no painel admin
        cursos = sorted(
            cursos,
            key=lambda c: (c.get("ordem") or 9999, c.get("titulo") or "")
        )

    except Exception as e:
        st.error(f"Erro ao buscar cursos: {e}")
        return

    if not cursos:
        st.info("Ainda não há cursos cadastrados.")
        return

    # ----- Filtros simples -----
    categorias = sorted(
        {c.get("categoria") or "Outros" for c in cursos if c.get("categoria")}
    )
    categorias_opcoes = ["Todas as categorias"] + categorias

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        categoria_escolhida = st.selectbox(
            "Filtrar por categoria:", categorias_opcoes, index=0
        )
    with col_f2:
        tipo = st.selectbox(
            "Tipo de curso:",
            ["Todos", "Somente gratuitos", "Somente pagos"],
            index=0,
        )

    cursos_filtrados = []
    for curso in cursos:
        if categoria_escolhida != "Todas as categorias":
            if (curso.get("categoria") or "Outros") != categoria_escolhida:
                continue

        if tipo == "Somente gratuitos" and not curso.get("gratuito"):
            continue
        if tipo == "Somente pagos" and curso.get("gratuito"):
            continue

        cursos_filtrados.append(curso)

    # ----- Grade de cards (3 por linha) -----
    colunas = st.columns(3)
    for idx, curso in enumerate(cursos_filtrados):
        col = colunas[idx % 3]
        with col:
            capa = curso.get("capa_url")
            if capa:
                st.image(capa, use_container_width=True)
            st.markdown(f"### {curso['titulo']}")

            categoria = curso.get("categoria") or "Sem categoria"
            st.caption(f"Categoria: {categoria}")

            gratuito = curso.get("gratuito", False)
            preco = float(curso.get("preco") or 0.0)

            if gratuito:
                st.markdown("🟢 **Gratuito**")
            else:
                preco_pix = preco * 0.9
                st.markdown(f"💰 R$ {preco:.2f}")
                st.caption(f"⚡ Pix: R$ {preco_pix:.2f} • 💳 até 6x sem juros")

            curso_id = curso["id"]
            liberados = st.session_state.get("cursos_liberados", [])
            comprados = st.session_state.get("comprados", [])
            liberado = gratuito or curso_id in liberados or curso_id in comprados

            if liberado:
                if st.button("▶️ Acessar", key=f"acessar_{curso_id}"):
                    st.session_state["curso_liberado"] = curso_id
                    st.session_state.pop("curso_espiar", None)
                    st.rerun()
            else:
                if st.button("💳 Comprar", key=f"comprar_{curso_id}"):
                    st.session_state["curso_checkout"] = curso_id
                    st.rerun()

            if st.button("👁 Espiar", key=f"espiar_{curso_id}"):
                st.session_state["curso_espiar"] = curso_id
                st.rerun()


# =========================
# CHECKOUT
# =========================


def tela_checkout(curso_id: int):
    st.title("💳 Finalizar Compra")

    try:
        r = httpx.get(f"{API_URL}/cursos/{curso_id}", headers=get_headers())
        if r.status_code != 200:
            st.error("Curso não encontrado.")
            return
        curso = r.json()
    except Exception as e:
        st.error(f"Erro ao buscar curso: {e}")
        return

    preco = float(curso.get("preco") or 0.0)

    st.markdown(f"**Curso:** {curso['titulo']}")
    st.markdown(f"**Valor original:** R$ {preco:.2f}")

    cupom = st.text_input("🎟 Cupom de desconto (opcional)")

    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("✅ Confirmar Pagamento"):
            try:
                r = httpx.post(
                    f"{API_URL}/cursos/{curso_id}/comprar",
                    params={"cupom": cupom or None},
                    headers=get_headers(),
                )
                if r.status_code == 200:
                    resposta = r.json()
                    msg = resposta.get("mensagem", "")
                    if "Curso liberado" in msg:
                        st.success("✅ Curso liberado automaticamente!")
                        st.session_state.setdefault("cursos_liberados", []).append(
                            curso_id
                        )
                        st.session_state["curso_liberado"] = curso_id
                        st.session_state.pop("curso_checkout", None)
                        st.rerun()
                    elif "pagamento_id" in resposta:
                        st.warning(
                            "⏳ Pagamento registrado. Aguarde a confirmação do gateway."
                        )
                        st.code(f"Pagamento ID: {resposta['pagamento_id']}")
                    else:
                        st.success("✅ Pedido registrado. Aguarde confirmação.")
                else:
                    st.error(
                        r.json().get("detail", "Erro ao finalizar compra no backend.")
                    )
            except Exception as e:
                st.error(f"Erro ao finalizar compra: {e}")

    with col2:
        if st.button("⬅️ Voltar para Cursos"):
            st.session_state.pop("curso_checkout", None)
            st.rerun()


# =========================
# MEUS CURSOS
# =========================


def tela_meus_cursos():
    st.title("📚 Meus Cursos")

    try:
        r = httpx.get(f"{API_URL}/cursos/", headers=get_headers())
        if r.status_code != 200:
            st.error("Erro ao carregar cursos.")
            return
        cursos = r.json()
        cursos = sorted(
            cursos,
            key=lambda c: (c.get("ordem") or 9999, c.get("titulo") or "")
        )

    except Exception as e:
        st.error(f"Erro ao buscar cursos: {e}")
        return

    aulas_concluidas = _carregar_progresso()
    cursos_liberados = st.session_state.get("cursos_liberados", [])
    cursos_comprados = st.session_state.get("comprados", [])

    filtro = st.radio(
        "🎯 Filtrar por:",
        ["Todos", "Gratuitos", "Pagos", "Em andamento", "Concluídos"],
        horizontal=True,
    )

    cursos_filtrados = []
    for curso in cursos:
        curso_id = curso["id"]
        gratuito = curso.get("gratuito", False)
        liberado = gratuito or curso_id in cursos_liberados or curso_id in cursos_comprados
        if not liberado:
            continue

        aulas = curso.get("aulas") or []
        total = len(aulas)
        feitas = len([a for a in aulas if a["id"] in aulas_concluidas])
        concluido = total > 0 and feitas == total

        if filtro == "Gratuitos" and not gratuito:
            continue
        if filtro == "Pagos" and gratuito:
            continue
        if filtro == "Em andamento" and (feitas == 0 or concluido):
            continue
        if filtro == "Concluídos" and not concluido:
            continue

        cursos_filtrados.append((curso, feitas, total, concluido))

    if not cursos_filtrados:
        st.info("Nenhum curso encontrado para esse filtro.")
        return

    for curso, feitas, total, concluido in cursos_filtrados:
        col1, col2 = st.columns([1, 3])
        with col1:
            if curso.get("capa_url"):
                st.image(curso["capa_url"], width=120)
        with col2:
            st.subheader(curso["titulo"])
            st.caption(f"Categoria: {curso.get('categoria') or 'Sem categoria'}")

            preco = float(curso.get("preco") or 0.0)
            gratuito = curso.get("gratuito", False)
            selo = ""
            if gratuito:
                selo += "🟢 **Gratuito** "
            else:
                preco_pix = preco * 0.9
                selo += f"💰 R$ {preco:.2f} | ⚡ Pix: **R$ {preco_pix:.2f}** "

            criado_em = curso.get("criado_em")
            if criado_em:
                try:
                    criado = datetime.datetime.fromisoformat(criado_em)
                    if (datetime.datetime.now() - criado).days <= 7:
                        selo += "🆕 **Novo** "
                except Exception:
                    pass

            if curso.get("destaque"):
                selo += "🔥 **Popular** "

            st.markdown(selo.strip() or "-")

            progresso = feitas / total if total else 0
            st.progress(progresso)
            st.caption(
                f"{feitas} de {total} aulas concluídas ({math.floor(progresso * 100) if total else 0}%)"
            )

            if st.button("▶️ Continuar", key=f"continuar_{curso['id']}"):
                st.session_state["curso_liberado"] = curso["id"]
                st.rerun()
