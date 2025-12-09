import os
import streamlit as st
import httpx
import plotly.graph_objects as go
from datetime import datetime

# Usa API_URL do ambiente; local = 127.0.0.1:8000
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")


def get_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}


def carregar_diagnostico():
    """
    Busca o diagnóstico salvo do usuário (se existir).
    """
    try:
        resp = httpx.get(
            f"{API_URL}/usuario/diagnostico",
            headers=get_headers(),
            timeout=20.0,
        )
        if resp.status_code == 200 and resp.json():
            diag = resp.json()
            nota = diag.get("nota_saude")
            respostas = diag.get("respostas_json") or {}
            return nota, respostas
        else:
            return None, {}
    except Exception:
        return None, {}


def tela_saude_empresa():
    # ------------------ CARREGA DIAGNÓSTICO SALVO ------------------
    nota_salva, respostas_salvas = carregar_diagnostico()

    st.title("❤️ Saúde da Empresa")

    if nota_salva is not None:
        st.info(f"🧾 Último diagnóstico salvo: **{nota_salva}%**")
    else:
        st.info("Você ainda não salvou nenhum diagnóstico. Responda abaixo para gerar o primeiro.")

    # ------------------ PERGUNTAS POR TEMA ------------------
    temas = {
        "Redes Sociais": [
            "Você está ativo nas redes sociais?",
            "Seu Instagram tem identidade visual profissional?",
            "Você publica conteúdos com frequência?",
            "Você analisa os resultados das postagens?",
        ],
        "Atendimento ao Cliente": [
            "Você responde os clientes rapidamente?",
            "Você tem um canal oficial de atendimento?",
            "O atendimento gera confiança no cliente?",
        ],
        "Vendas e Prospecção": [
            "Você tem uma rotina clara de prospecção?",
            "Você tem metas de vendas definidas?",
            "Você oferece formas de pagamento facilitadas?",
        ],
    }

    resultados = {}
    respostas = {}

    # ------------------ SLIDERS + MÉDIAS POR TEMA ------------------
    for tema, perguntas in temas.items():
        st.markdown(f"### 📌 {tema}")
        total = 0
        respostas[tema] = {}

        for pergunta in perguntas:
            # Se tiver diagnóstico salvo, tenta puxar aquele valor
            valor_salvo = (
                respostas_salvas.get(tema, {}).get(pergunta, 50)
                if respostas_salvas
                else 50
            )

            valor = st.slider(
                pergunta,
                0,
                100,
                int(valor_salvo),
                step=5,
                key=f"{tema}_{pergunta}",
            )
            respostas[tema][pergunta] = valor
            total += valor

        media = round(total / len(perguntas), 2)
        resultados[tema] = media
        st.markdown(f"✅ **Nota neste tema: {media}%**")
        st.divider()

    if not resultados:
        st.warning("Ajuste os sliders para gerar o diagnóstico.")
        return

    # ------------------ MÉDIA GERAL + GRÁFICO RADAR ------------------
    media_geral = round(sum(resultados.values()) / len(resultados), 2)
    st.success(f"🏁 Média geral da empresa: {media_geral}%")

    categorias = list(resultados.keys())
    valores = list(resultados.values())
    valores.append(valores[0])
    categorias.append(categorias[0])

    fig = go.Figure(
        data=go.Scatterpolar(
            r=valores,
            theta=categorias,
            fill="toself",
            name="Saúde da Empresa",
        )
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100]),
        ),
        showlegend=False,
        title="📊 Diagnóstico - Gráfico Radar",
    )

    st.plotly_chart(fig, use_container_width=True)

    # ------------------ SALVAR DIAGNÓSTICO ------------------
    if st.button("💾 Salvar diagnóstico"):
        with st.spinner("Salvando diagnóstico..."):
            try:
                payload = {
                    "nota_saude": media_geral,
                    "respostas_json": respostas,
                }

                resp = httpx.post(
                    f"{API_URL}/usuario/diagnostico",
                    headers=get_headers(),
                    json=payload,
                    timeout=20.0,
                )

                if resp.status_code == 200:
                    st.success("✅ Diagnóstico salvo com sucesso!")

                    # Atualiza nota/respostas em memória imediatamente
                    st.session_state["ultima_nota_saude"] = media_geral
                else:
                    st.error("❌ Erro ao salvar no banco de dados.")
                    st.caption(
                        f"Código HTTP: {resp.status_code} | Resposta: {resp.text[:300]}"
                    )

            except Exception as e:
                st.error(f"Erro na conexão ao salvar: {e}")

    # ------------------ 'HISTÓRICO' (ÚLTIMO DIAGNÓSTICO) ------------------
    st.header("📅 Histórico de Diagnósticos")

    if nota_salva is not None:
        st.write(f"- Último diagnóstico salvo: **{nota_salva}%**")
        st.caption("*(O sistema guarda sempre o diagnóstico mais recente por enquanto.)*")
    else:
        st.info("Nenhum diagnóstico salvo ainda.")
