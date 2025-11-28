import streamlit as st
import httpx
import plotly.graph_objects as go
from datetime import datetime

API_URL = "https://mivmark-backend.onrender.com"

def get_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}

def tela_saude_empresa():

    # Pega nota e respostas salvas, ou valores padrão
    nota_salva = st.session_state.dados_usuario.get("nota_saude")
    respostas_salvas = st.session_state.dados_usuario.get("respostas_saude") or {}
    nota_exibida = nota_salva if nota_salva else "-"

    st.title(f"❤️ Saúde da Empresa: {nota_exibida}")

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
        ]
    }

    resultados = {}
    respostas = {}

    # Calcula médias por tema e monta sliders
    for tema, perguntas in temas.items():
        st.markdown(f"### 📌 {tema}")
        total = 0
        respostas[tema] = {}
        for pergunta in perguntas:
            valor_salvo = respostas_salvas.get(tema, {}).get(pergunta, 50)
            valor = st.slider(pergunta, 0, 100, valor_salvo, step=25, key=f"{tema}_{pergunta}")
            respostas[tema][pergunta] = valor
            total += valor
        media = round(total / len(perguntas), 2)
        resultados[tema] = media
        st.markdown(f"✅ **Nota neste tema: {media}%**")
        st.divider()

    if resultados:
        media_geral = round(sum(resultados.values()) / len(resultados), 2)
        st.success(f"🏁 Média geral da empresa: {media_geral}%")

        # --- Gráfico Radar ---
        categorias = list(resultados.keys())
        valores = list(resultados.values())
        valores.append(valores[0])  # fecha o gráfico
        categorias.append(categorias[0])

        fig = go.Figure(data=go.Scatterpolar(
            r=valores,
            theta=categorias,
            fill='toself',
            name='Saúde da Empresa'
        ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )),
            showlegend=False,
            title="📊 Diagnóstico - Gráfico Radar"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Botão salvar diagnóstico
        if st.button("💾 Salvar diagnóstico"):
            with st.spinner("Salvando diagnóstico..."):
                try:
                    response = httpx.put(
                        f"{API_URL}/usuario/nota_saude",
                        headers=get_headers(),
                        json={"nota": media_geral, "respostas": respostas}
                    )
                    if response.status_code == 200:
                        usuario_atualizado = httpx.get(
                            f"{API_URL}/minha-conta",
                            headers=get_headers()
                        )
                        if usuario_atualizado.status_code == 200:
                            st.session_state.dados_usuario = usuario_atualizado.json()
                            st.success("✅ Diagnóstico salvo com sucesso!")
                            try:
                                st.experimental_rerun()
                            except AttributeError:
                                st.session_state.reload_page = not st.session_state.get("reload_page", False)
                        else:
                            st.warning("⚠️ Salvou, mas não atualizou os dados da sessão.")
                    else:
                        st.error("❌ Erro ao salvar no banco de dados.")
                except Exception as e:
                    st.error(f"Erro na conexão: {e}")

        # --- Histórico de diagnósticos ---
        st.header("📅 Histórico de Diagnósticos")

        try:
            resp = httpx.get(f"{API_URL}/usuario/diagnosticos", headers=get_headers())
            if resp.status_code == 200:
                historico = resp.json()
                if historico:
                    for diag in historico[:5]:  # últimos 5
                        data_str = datetime.fromisoformat(diag["data"]).strftime("%d/%m/%Y %H:%M")
                        st.write(f"- {data_str}: **{diag['nota']}%**")
                else:
                    st.info("Nenhum diagnóstico salvo ainda.")
            else:
                st.error("Erro ao carregar histórico.")
        except Exception as e:
            st.error(f"Erro na conexão do histórico: {e}")

    if st.session_state.get("reload_page"):
        try:
            st.experimental_rerun()
        except Exception:
            pass
