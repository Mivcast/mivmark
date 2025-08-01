import streamlit as st
import httpx

API_URL = "http://127.0.0.1:8000"

def get_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}

# ------------------------
# CURSO COM AULAS E PROGRESSO
# ------------------------

def tela_curso(curso_id):
    try:
        r = httpx.get(f"{API_URL}/cursos/{curso_id}", headers=get_headers())
        curso = r.json()
    except:
        st.error("Erro ao buscar curso.")
        return

    st.title(curso["titulo"])
    if curso.get("capa_url"):
        st.image(curso["capa_url"], use_container_width=True)
    st.markdown(f"**Categoria:** {curso['categoria']}")
    st.markdown(curso["descricao"])
    st.markdown("---")

    st.subheader("🎥 Aulas Disponíveis")

    aulas_concluidas = []
    try:
        p = httpx.get(f"{API_URL}/cursos/progresso", headers=get_headers())
        if p.status_code == 200:
            aulas_concluidas = p.json().get("aulas_concluidas", [])
    except Exception as e:
        st.warning(f"Não foi possível carregar o progresso: {e}")

    for aula in sorted(curso["aulas"], key=lambda a: a["ordem"]):
        concluida = aula["id"] in aulas_concluidas
        st.markdown(f"### {aula['titulo']}")
        st.caption(aula["descricao"])
        st.video(aula["video_url"])

        if not concluida:
            if st.button("✅ Marcar como concluída", key=f"concluir_{aula['id']}"):
                httpx.post(f"{API_URL}/cursos/aula/{aula['id']}/concluir", headers=get_headers())
                st.success("Marcado como concluído!")
                st.rerun()
        else:
            st.success("✔️ Aula concluída")
        st.divider()

    if st.button("⬅️ Voltar para Cursos"):
        st.session_state.pop("curso_liberado", None)
        st.rerun()

# ------------------------
# LISTAGEM DE CURSOS
# ------------------------

def tela_cursos():
    import datetime

    st.title("🎓 Nossos Cursos")

    try:
        r = httpx.get(f"{API_URL}/cursos/", headers=get_headers())
        if r.status_code != 200:
            st.error("Erro ao carregar cursos.")
            return
        cursos = r.json()
    except Exception as e:
        st.error(f"Erro: {e}")
        return

    r2 = httpx.get(f"{API_URL}/cursos/progresso", headers=get_headers())
    ids_concluidos = []
    if r2.status_code == 200:
        ids_concluidos = r2.json().get("aulas_concluidas", [])

    colunas = st.columns(4)
    for idx, curso in enumerate(cursos):
        col = colunas[idx % 4]
        with col:
            st.image(curso["capa_url"], use_container_width=True)
            st.markdown(f"### {curso['titulo']}")

            # ⭐ Estrelas de avaliação (simulação por enquanto)
            nota = curso.get("avaliacao_media", 4.2)  # pode vir da API no futuro
            estrelas = "⭐" * int(nota) + "☆" * (5 - int(nota))
            st.caption(f"{estrelas} {nota:.1f}")

            # 🆕 Verifica se é novo (últimos 7 dias)
            criado_em = curso.get("criado_em")
            if criado_em:
                criado = datetime.datetime.fromisoformat(criado_em)
                if (datetime.datetime.now() - criado).days <= 7:
                    st.markdown("🆕 **Novo**")

            # 🔥 Curso em destaque
            if curso.get("destaque"):
                st.markdown("🔥 **Popular**")

            # 💥 Promoção
            preco = curso.get("preco") or 0.0
            if preco and preco < 50:
                st.markdown("💥 **Em promoção**")

            # 🟢 Gratuito
            if curso["gratuito"]:
                st.markdown("🟢 **Gratuito**")
            else:
                preco_pix = preco * 0.9
                st.markdown(f"💰 R$ {preco:.2f}")
                st.markdown(f"⚡ Pix: **R$ {preco_pix:.2f}** • 💳 6x sem juros")

            curso_id = curso["id"]
            liberado = curso["gratuito"] or curso_id in st.session_state.get("cursos_liberados", [])

            if liberado:
                if st.button("▶️ Acessar", key=f"acessar_{curso_id}"):
                    st.session_state["curso_selecionado"] = curso_id
                    st.rerun()
            elif curso_id in st.session_state.get("comprados", []):
                st.success("✅ Já comprado")
                if st.button("▶️ Continuar", key=f"continuar_{curso_id}"):
                    st.session_state["curso_selecionado"] = curso_id
                    st.rerun()
            else:
                if st.button("💳 Comprar", key=f"comprar_{curso_id}"):
                    st.session_state["curso_checkout"] = curso_id
                    st.rerun()

            if st.button("👁 Espiar", key=f"espiar_{curso_id}"):
                st.session_state["curso_espiar"] = curso_id
                st.rerun()

# ------------------------
# DETALHE DO CURSO (ESPIAR)
# ------------------------

def tela_curso(curso_id):
    import math

    try:
        r = httpx.get(f"{API_URL}/cursos/{curso_id}", headers=get_headers())
        curso = r.json()
    except:
        st.error("Erro ao buscar curso.")
        return

    st.title(curso["titulo"])
    st.image(curso["capa_url"], use_container_width=True)
    st.markdown(f"**Categoria:** {curso['categoria']}")
    st.markdown(curso["descricao"])

    st.markdown("---")
    st.subheader("📊 Progresso no Curso")

    # Aulas concluídas
    aulas_concluidas = []
    try:
        p = httpx.get(f"{API_URL}/cursos/progresso", headers=get_headers())
        aulas_concluidas = p.json().get("aulas_concluidas", [])
    except:
        pass

    total_aulas = len(curso["aulas"])
    feitas = len([a for a in curso["aulas"] if a["id"] in aulas_concluidas])
    progresso = feitas / total_aulas if total_aulas > 0 else 0

    st.progress(progresso)
    st.caption(f"{feitas} de {total_aulas} aulas concluídas ({math.floor(progresso*100)}%)")

    st.markdown("---")
    st.subheader("🎥 Aulas do Curso")

    for aula in sorted(curso["aulas"], key=lambda a: a["ordem"]):
        concluida = aula["id"] in aulas_concluidas
        st.markdown(f"#### {aula['titulo']} {'✔️' if concluida else ''}")
        st.write(aula["descricao"])
        st.video(aula["video_url"])

        if not concluida:
            if st.button("✅ Marcar como concluída", key=f"concluir_{aula['id']}"):
                httpx.post(f"{API_URL}/cursos/aula/{aula['id']}/concluir", headers=get_headers())
                st.success("Aula marcada como concluída!")
                st.rerun()
        else:
            st.success("✔️ Aula já concluída")

        st.divider()

    if st.button("⬅️ Voltar para Cursos"):
        st.session_state.pop("curso_liberado", None)
        st.session_state.pop("curso_selecionado", None)
        st.rerun()

# ------------------------
# CHECKOUT
# ------------------------

def tela_checkout(curso_id):
    with st.sidebar:
        st.title("📚 Menu")
        if st.button("⬅️ Voltar para Cursos"):
            st.session_state.pop("curso_checkout", None)
            st.rerun()

    st.title("💳 Finalizar Compra")
    st.info("Confira os detalhes antes de finalizar sua compra.")

    try:
        r = httpx.get(f"{API_URL}/cursos/{curso_id}", headers=get_headers())
        if r.status_code != 200:
            st.error("Curso não encontrado.")
            return
        curso = r.json()
    except Exception as e:
        st.error(f"Erro ao buscar curso: {e}")
        return

    preco = curso.get("preco") or 0.0
    st.markdown(f"**Curso:** {curso['titulo']}")
    st.markdown(f"**Valor original:** R$ {preco:.2f}")

    cupom = st.text_input("🎟 Cupom de desconto (opcional)")

    if st.button("✅ Confirmar Pagamento"):
        try:
            headers = get_headers()
            r = httpx.post(
                f"{API_URL}/cursos/{curso_id}/comprar",
                params={"cupom": cupom},
                headers=headers
            )
            if r.status_code == 200:
                resposta = r.json()
                if "Curso liberado" in resposta["mensagem"]:
                    st.success("✅ Curso liberado automaticamente com cupom de 100%!")
                    st.session_state["curso_liberado"] = curso_id
                    st.session_state.pop("curso_checkout", None)
                    st.rerun()
                elif "pagamento_id" in resposta:
                    st.warning("⏳ Pagamento registrado. Aguardando confirmação...")
                    st.code(f"Pagamento ID: {resposta['pagamento_id']}")
                else:
                    st.success("✅ Pedido registrado, aguarde confirmação.")
            else:
                st.error(r.json().get("detail", "Erro ao finalizar compra."))
        except Exception as e:
            st.error(f"Erro: {e}")




def tela_meus_cursos():
    import math
    import datetime

    st.title("📚 Meus Cursos")

    try:
        r = httpx.get(f"{API_URL}/cursos/", headers=get_headers())
        cursos = r.json()
    except:
        st.error("Erro ao buscar cursos.")
        return

    try:
        progresso = httpx.get(f"{API_URL}/cursos/progresso", headers=get_headers()).json()
    except:
        progresso = {"aulas_concluidas": []}

    aulas_concluidas = progresso.get("aulas_concluidas", [])
    cursos_liberados = st.session_state.get("cursos_liberados", [])
    cursos_comprados = st.session_state.get("comprados", [])

    filtro = st.radio("🎯 Filtrar por:", ["Todos", "Gratuitos", "Pagos", "Em Andamento", "Concluídos"], horizontal=True)
    cursos_filtrados = []

    for curso in cursos:
        curso_id = curso["id"]
        liberado = curso["gratuito"] or curso_id in cursos_liberados or curso_id in cursos_comprados
        if not liberado:
            continue

        total = len(curso["aulas"])
        feitas = len([a for a in curso["aulas"] if a["id"] in aulas_concluidas])
        concluido = total > 0 and feitas == total

        if filtro == "Gratuitos" and not curso["gratuito"]:
            continue
        if filtro == "Pagos" and curso["gratuito"]:
            continue
        if filtro == "Em Andamento" and (feitas == 0 or concluido):
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
            st.image(curso["capa_url"], width=120)
        with col2:
            st.subheader(curso["titulo"])
            st.caption(f"Categoria: {curso['categoria']}")

            # Selos visuais
            preco = curso.get("preco") or 0.0
            criado_em = curso.get("criado_em")
            nota = curso.get("avaliacao_media", 4.3)
            estrelas = "⭐" * int(nota) + "☆" * (5 - int(nota))

            selo = ""
            if curso["gratuito"]:
                selo += "🟢 **Gratuito** "
            else:
                preco_pix = preco * 0.9
                selo += f"💰 R$ {preco:.2f} | ⚡ Pix: **R$ {preco_pix:.2f}** "
                if preco < 50:
                    selo += "💥 **Promoção** "

            if curso.get("destaque"):
                selo += "🔥 **Popular** "
            if criado_em:
                criado = datetime.datetime.fromisoformat(criado_em)
                if (datetime.datetime.now() - criado).days <= 7:
                    selo += "🆕 **Novo** "

            st.markdown(selo.strip())
            st.caption(f"{estrelas} {nota:.1f}")

            # Progresso
            st.progress(feitas / total if total else 0)
            st.caption(f"{feitas} de {total} aulas concluídas ({math.floor((feitas / total) * 100) if total else 0}%)")

            if st.button("▶️ Continuar", key=f"continuar_{curso['id']}"):
                st.session_state["curso_liberado"] = curso["id"]
                st.rerun()
