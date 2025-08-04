import streamlit as st
import httpx
from datetime import datetime, timedelta
import json
import streamlit.components.v1 as components
from frontend.verificar_acesso import usuario_tem_acesso

API_URL = "http://127.0.0.1:8000"

def exibir_calendario_html(eventos):
    eventos_js = json.dumps([
        {
            "title": e["titulo"],
            "start": e["data_inicio"].split(".")[0],
            "end": e["data_fim"].split(".")[0],
            "color": definir_cor_evento(e),
        } for e in eventos
    ])

    html_code = f"""
    <div id='calendar'></div>
    <link href='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.4/index.global.min.css' rel='stylesheet' />
    <script src='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.4/index.global.min.js'></script>
    <script>
        document.addEventListener('DOMContentLoaded', function () {{
            var calendarEl = document.getElementById('calendar');
            var calendar = new FullCalendar.Calendar(calendarEl, {{
                initialView: 'dayGridMonth',
                locale: 'pt-br',
                height: 650,
                themeSystem: 'standard',
                headerToolbar: {{
                    left: 'prev,next today',
                    center: 'title',
                    right: 'dayGridMonth,timeGridWeek,timeGridDay'
                }},
                events: {eventos_js},
                eventDidMount: function(info) {{
                    info.el.style.backgroundColor = info.event.backgroundColor;
                    info.el.style.color = 'white';
                    info.el.style.padding = '2px';
                    info.el.style.borderRadius = '5px';
                }}
            }});
            calendar.render();
        }});
    </script>
    """
    components.html(html_code, height=700)

def definir_cor_evento(evento):
    cores = {
        "reuniao": "#0d6efd",
        "tarefa": "#6610f2",
        "evento": "#20c997",
        "campanha": "#0dcaf0",
        "outro": "#6c757d"
    }
    return cores.get(evento["tipo_evento"].lower(), "#888888")

def tela_agenda():
    if not usuario_tem_acesso("agenda"):
        st.warning("⚠️ Este módulo está disponível apenas para planos pagos.")
        st.stop()


    try:
        usuario_id = st.session_state.dados_usuario.get("id", 1)
        r = httpx.get(f"{API_URL}/agenda/{usuario_id}")
        if r.status_code == 200:
            eventos = r.json()
            if eventos:
                st.markdown("<br>", unsafe_allow_html=True)
                with st.container():
 
                    st.markdown("<div style='padding:10px; background-color:#fff;'>", unsafe_allow_html=True)
                    exibir_calendario_html(eventos)
                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.info("Nenhum evento encontrado.")
        else:
            st.error("Erro ao carregar eventos.")
    except Exception as e:
        st.error(f"Erro na requisição: {e}")

    st.markdown("---")
    with st.expander("➕ Adicionar / Editar Evento", expanded=False):
        if "evento_em_edicao" not in st.session_state:
            st.session_state.evento_em_edicao = None
        evento_editar = st.session_state.evento_em_edicao

        with st.form("form_evento"):
            if evento_editar:
                titulo = st.text_input("Título", value=evento_editar["titulo"])
                descricao = st.text_area("Descrição", value=evento_editar.get("descricao", ""))
                data_inicio = datetime.fromisoformat(evento_editar["data_inicio"])
                hora_inicio = data_inicio.time()
                data_fim = datetime.fromisoformat(evento_editar["data_fim"])
                hora_fim = data_fim.time()
                tipo_padrao = evento_editar["tipo_evento"]
                prioridade_padrao = evento_editar["prioridade"]
                visivel_cliente = evento_editar["visivel_cliente"]
            else:
                titulo = st.text_input("Título", max_chars=100)
                descricao = st.text_area("Descrição")
                data_inicio = st.date_input("Data de início", value=datetime.now())
                hora_inicio = st.time_input("Hora de início", value=datetime.now().time())
                data_fim = st.date_input("Data de fim", value=datetime.now())
                hora_fim = st.time_input("Hora de fim", value=(datetime.now() + timedelta(hours=1)).time())
                tipo_padrao = "outro"
                prioridade_padrao = "media"
                visivel_cliente = False

            opcoes_tipo = {
                "Reunião": "reuniao",
                "Tarefa": "tarefa",
                "Evento": "evento",
                "Campanha": "campanha",
                "Outro": "outro"
            }
            tipo_legivel = [k for k, v in opcoes_tipo.items() if v == tipo_padrao][0]
            tipo_evento_legivel = st.selectbox("Tipo", list(opcoes_tipo.keys()), index=list(opcoes_tipo.keys()).index(tipo_legivel))
            tipo_evento = opcoes_tipo[tipo_evento_legivel]

            opcoes_prioridade = {
                "Baixa": "baixa",
                "Média": "media",
                "Alta": "alta"
            }
            prioridade_legivel = [k for k, v in opcoes_prioridade.items() if v == prioridade_padrao][0]
            prioridade_selecionada = st.selectbox("Prioridade", list(opcoes_prioridade.keys()), index=list(opcoes_prioridade.keys()).index(prioridade_legivel))
            prioridade = opcoes_prioridade[prioridade_selecionada]

            visivel_cliente = st.checkbox("Visível para o cliente?", value=visivel_cliente)

            botao = "Salvar alterações" if evento_editar else "Salvar evento"
            enviado = st.form_submit_button(botao)

        if enviado:
            inicio = datetime.combine(data_inicio, hora_inicio)
            fim = datetime.combine(data_fim, hora_fim)


            evento = {
                "titulo": titulo,
                "descricao": descricao,
                "data_inicio": inicio.isoformat(),
                "data_fim": fim.isoformat(),
                "tipo_evento": tipo_evento_legivel,  # <- agora em formato correto
                "prioridade": prioridade_selecionada,  # <- idem
                "origem": "Manual",  # <- já está certo
                "recorrencia": None,
                "visivel_cliente": visivel_cliente,
                "usuario_id": st.session_state.dados_usuario.get("id", 1)
            }

            try:
                if evento_editar:
                    evento_id = evento_editar["id"]
                    r = httpx.put(f"{API_URL}/agenda/{evento_id}", json=evento)
                else:
                    r = httpx.post(f"{API_URL}/agenda/", json=evento)

                if r.status_code in (200, 201):
                    st.success("✅ Evento salvo com sucesso!")
                    st.session_state.evento_em_edicao = None
                    st.rerun()
                else:
                    st.error(f"Erro ao salvar evento: {r.text}")
            except Exception as e:
                st.error(f"Erro na requisição: {e}")

    st.markdown("---")
    st.subheader("📌 Eventos Cadastrados")

    try:
        usuario_id = st.session_state.dados_usuario.get("id", 1)
        r = httpx.get(f"{API_URL}/agenda/{usuario_id}")
        if r.status_code == 200:
            eventos = r.json()
            for evento in eventos:
                col1, col2 = st.columns([6, 1])
                with col1:
                    tipo_icon = {
                        "reuniao": "📅",
                        "tarefa": "📝",
                        "evento": "🎉",
                        "campanha": "📢",
                        "outro": "📌"
                    }.get(evento['tipo_evento'].lower(), "📌")
                    st.markdown(f"**{tipo_icon} {evento['titulo']}** → _{evento['data_inicio'].split('T')[0]} {evento['data_inicio'].split('T')[1][:5]}_ ➝ _{evento['data_fim'].split('T')[0]} {evento['data_fim'].split('T')[1][:5]}_  | 🔥 {evento['prioridade'].capitalize()}")
                with col2:
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("✏️", key=f"edit_{evento['id']}"):
                            st.session_state.evento_em_edicao = evento
                            st.rerun()
                    with col_b:
                        if st.button("🗑️", key=f"del_{evento['id']}"):
                            try:
                                resp = httpx.delete(f"{API_URL}/agenda/{evento['id']}")
                                if resp.status_code == 200:
                                    st.success("Evento excluído com sucesso.")
                                    st.rerun()
                                else:
                                    st.error("Erro ao excluir evento.")
                            except Exception as e:
                                st.error(f"Erro na requisição: {e}")
        else:
            st.error("Erro ao carregar eventos.")
    except Exception as e:
        st.error(f"Erro na requisição: {e}")
