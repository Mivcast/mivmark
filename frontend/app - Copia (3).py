import streamlit as st
import os  
from pathlib import Path
from agenda import tela_agenda  # ✅ Importa a versão visual com calendário
from datetime import datetime, timedelta

# ⚙️ A configuração da página deve ser a PRIMEIRA chamada do Streamlit
st.set_page_config(layout="wide")

hide_streamlit_chrome = """
<style>
/* Esconde o menu dos 3 pontinhos do Streamlit */
#MainMenu {visibility: hidden;}

/* Esconde o rodapé "Made with Streamlit" */
footer {visibility: hidden;}

/* Esconde o botão "Deploy" padrão do Streamlit */
.stDeployButton {display: none !important;}
</style>
"""
st.markdown(hide_streamlit_chrome, unsafe_allow_html=True)


import httpx
import datetime
import streamlit.components.v1 as components
from site_cliente import tela_site_cliente
from aplicativos import listar_aplicativos_admin
from admin.planos import aba_gerenciar_planos



API_URL = os.getenv("API_URL", "").strip().rstrip("/")

if not API_URL:
    API_URL = "http://127.0.0.1:8000"

# ✅ garante que o app inteiro (todas as telas) use o mesmo API_URL
if "API_URL" not in st.session_state:
    st.session_state["API_URL"] = API_URL




def usuario_tem_acesso(modulo: str) -> bool:
    usuario = st.session_state.get("dados_usuario", {}) or {}
    plano = usuario.get("plano_atual")

    if not plano:
        return False

    # 🔁 Compatibilidade: tratar consultoria_full como plano Profissional
    if str(plano).lower() == "consultoria_full":
        plano = "Profissional"

    try:
        r = httpx.get(f"{API_URL}/planos/")
        if r.status_code == 200:
            planos = r.json()
            for p in planos:
                if p["nome"] == plano:
                    return modulo in p.get("modulos_liberados", [])
    except Exception as e:
        st.warning(f"Erro ao verificar acesso ao módulo: {e}")
    
    return False

    try:
        r = httpx.get(f"{API_URL}/planos/")
        if r.status_code == 200:
            planos = r.json()
            for p in planos:
                if p["nome"] == plano:
                    return modulo in p.get("modulos_liberados", [])
    except Exception as e:
        st.warning(f"Erro ao verificar acesso ao módulo: {e}")
    
    return False




def mostrar_bloqueio_modulo(nome_modulo: str):
    """
    Mostra mensagem específica quando o usuário não tem acesso ao módulo:
    - Se o teste gratuito de 3 dias já terminou → aviso de teste expirado
    - Caso contrário → aviso genérico de módulo pago
    """
    usuario = st.session_state.get("dados_usuario", {}) or {}
    plano = usuario.get("plano_atual") or "Gratuito"
    expira_str = usuario.get("plano_expira_em")

    mostrou_mensagem_teste = False

    # 🔎 Só faz sentido falar de teste expirado se ele estiver no plano Gratuito
    # e existir uma data de expiração salva
    if plano == "Gratuito" and expira_str:
        try:
            # expira_str vem do backend como ISO. Garantimos que não tenha "Z" no final
            if isinstance(expira_str, str):
                expira_dt = datetime.fromisoformat(expira_str.replace("Z", ""))
            else:
                expira_dt = expira_str

            if expira_dt < datetime.utcnow():
                data_fmt = expira_dt.strftime("%d/%m/%Y")
                st.error(f"⏰ Seu teste gratuito de 3 dias terminou em **{data_fmt}**.")
                st.info(
                    f"Para continuar usando o módulo **{nome_modulo}**, "
                    f"faça upgrade do seu plano na opção **'💳 Plano Atual'** do menu lateral."
                )
                mostrou_mensagem_teste = True
        except Exception:
            # Se der erro pra interpretar a data, cai no aviso genérico abaixo
            pass

    if not mostrou_mensagem_teste:
        st.warning(f"⚠️ O módulo **{nome_modulo}** está disponível apenas para planos pagos.")
        st.info(
            "Para liberar esse recurso, faça upgrade do seu plano na opção "
            "**'💳 Plano Atual'** do menu lateral."
        )




# ------------------- ESTADO GLOBAL -------------------

if "token" not in st.session_state:
    st.session_state.token = None
if "dados_usuario" not in st.session_state:
    st.session_state.dados_usuario = {}
if "admin" not in st.session_state:
    st.session_state.admin = False
if "chat" not in st.session_state:
    st.session_state.chat = []



# ------------------- FUNÇÕES DE BACKEND -------------------


def tela_inicio():
    import streamlit as st
    import datetime
    import base64
    from pathlib import Path

    usuario = st.session_state.get("dados_usuario", {})

    # ---------------------------------------------------------
    # 🔔 AVISO SOBRE O TESTE GRATUITO DE 3 DIAS
    # ---------------------------------------------------------
    plano = usuario.get("plano_atual", "Gratuito")
    expira_str = usuario.get("plano_expira_em")

    if expira_str:
        try:
            from datetime import datetime
            expira_dt = datetime.fromisoformat(expira_str.replace("Z", ""))

            hoje = datetime.utcnow()
            dias_restantes = (expira_dt.date() - hoje.date()).days

            if plano == "Profissional" and dias_restantes > 0:
                st.markdown(
                    f"""
                    <div style="padding: 15px; border-radius: 10px; 
                        background: linear-gradient(90deg, #0066ff, #00bbff);
                        color: white; margin-bottom: 20px;">
                        <h4>⏳ Seu teste gratuito está ativo!</h4>
                        <p>Você ainda tem <b>{dias_restantes} dias</b> de acesso ao 
                        <b>Plano Profissional</b>.</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            elif plano == "Gratuito" and expira_dt < hoje:
                data_fmt = expira_dt.strftime("%d/%m/%Y")
                st.markdown(
                    f"""
                    <div style="padding: 15px; border-radius: 10px; 
                        background: #fff3cd; border: 1px solid #ffeeba;
                        color: #856404; margin-bottom: 20px;">
                        <h4>⏰ Seu teste gratuito terminou</h4>
                        <p>O seu acesso ao plano profissional expirou em 
                        <b>{data_fmt}</b>.</p>
                        <p>Para continuar com todas as funcionalidades, faça o upgrade do seu plano.</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        except Exception as e:
            pass


    nome = usuario.get("nome", "Usuário")
    plano = usuario.get("plano_atual") or "Gratuito"
    if usuario.get("is_admin"):
        plano = "Administrador (acesso total)"

    usuario_id = usuario.get("id")
    nota_saude = usuario.get("nota_saude") or "Não realizado"
    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    import httpx
    API_URL = "https://mivmark-backend.onrender.com"

    # Caminhos das imagens
    BASE_DIR = Path(__file__).parent
    caminho_desktop = BASE_DIR / "img" / "full_banner_inicio.png"
    caminho_mobile = BASE_DIR / "img" / "mini_full_banner_inicio.png"

    def carregar_base64(caminho_img):
        with open(caminho_img, "rb") as f:
            return base64.b64encode(f.read()).decode()

    try:
        banner_desktop = carregar_base64(caminho_desktop)
        banner_mobile = carregar_base64(caminho_mobile)
    except:
        banner_desktop = banner_mobile = ""

    # Banner responsivo
    st.markdown(f"""
    <style>
        .banner-container {{
            width: 100%;
            margin-bottom: 20px;
        }}
        .banner-desktop {{ display: block; }}
        .banner-mobile {{ display: none; }}
        @media (max-width: 768px) {{
            .banner-desktop {{ display: none; }}
            .banner-mobile {{ display: block; }}
        }}
    </style>
    <div class="banner-container">
        {"<img src='data:image/png;base64," + banner_desktop + "' class='banner-desktop' style='width: 100%; border-radius: 10px;' />" if banner_desktop else ""}
        {"<img src='data:image/png;base64," + banner_mobile + "' class='banner-mobile' style='width: 100%; border-radius: 10px;' />" if banner_mobile else ""}
    </div>
    """, unsafe_allow_html=True)


    st.success(f"Olá, **{nome}**! Você está no plano **{plano}**.")

    # Desconto promocional
    st.markdown("""
    <div style="background-color: #e0fce2; border: 1px solid #b2f5c2; border-radius: 8px; padding: 10px 20px; margin-top: 15px; margin-bottom: 25px;">
        <strong>🎁 Você tem um desconto exclusivo!</strong><br>
        Escolha seu plano e ganhe 25% de desconto no primeiro pagamento. 
        <a href="#" style="color: #007bff;">Escolher plano</a>
    </div>
    """, unsafe_allow_html=True)

    # Progresso Consultoria
    try:
        r = httpx.get(f"{API_URL}/consultoria/progresso", headers=headers)
        progresso = r.json()
        total = len(progresso)
        concluidos = sum(1 for p in progresso.values() if p["concluido"])
        pct_consultoria = int((concluidos / total) * 100) if total > 0 else 0
    except:
        pct_consultoria = 0

    # Progresso Cursos
    try:
        r = httpx.get(f"{API_URL}/cursos/progresso", headers=headers)
        if r.status_code == 200:
            dados = r.json()
            # Backend retorna lista de IDs de aulas concluídas
            lista_concluidas = dados.get("aulas_concluidas", [])
            concluidas = len(lista_concluidas)

            # Por enquanto, assumimos total mínimo de 1
            # (depois podemos buscar o total real de aulas no backend)
            total = max(concluidas, 1)
            pct_curso = int((concluidas / total) * 100) if total > 0 else 0
        else:
            pct_curso = 0
    except Exception:
        pct_curso = 0


    # Estilo dos cards personalizados
    st.markdown(f"""
    <style>
        .grid-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
        }}
        .card-novo {{
            background: linear-gradient(to bottom, #dbeeff, #f5faff);
            border-radius: 16px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
        }}
        .card-novo h3 {{
            font-size: 22px;
            color: #3366ff;
            margin-bottom: 5px;
        }}
        .card-novo .pct {{
            font-size: 36px;
            font-weight: bold;
            color: #000;
            margin: 10px 0 0;
        }}
        .card-novo .label {{
            font-size: 16px;
            margin-bottom: 15px;
        }}
        .card-novo .botao {{
            display: inline-block;
            margin: 10px 0;
            background-color: #e5f0ff;
            color: #3366ff;
            padding: 8px 20px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: bold;
            font-size: 14px;
        }}
        .card-novo .cta {{
            font-size: 14px;
            color: #000;
            margin-top: 10px;
        }}
        .gauge {{
            width: 60px;
            height: 60px;
            margin: 10px auto;
            background: conic-gradient(#3366ff VAR_DEG, #e0e0e0 0deg);
            border-radius: 50%;
            position: relative;
        }}
        .gauge::after {{
            content: "";
            position: absolute;
            top: 50%;
            left: 50%;
            width: 20px;
            height: 20px;
            background: #fff;
            border-radius: 50%;
            transform: translate(-50%, -50%);
        }}
    </style>

    <div class="grid-cards">
        <div class="card-novo">
            <h3>Consultoria</h3>
            <div class="gauge" style="background: conic-gradient(#3366ff {pct_consultoria * 3.6}deg, #e0e0e0 0deg);"></div>
            <div class="pct">{pct_consultoria}%</div>
            <div class="label">dos tópicos concluídos</div>
            <a href="#" class="botao">Acessar Consultoria</a>
            <div class="cta">Continue a melhorar todos os setores da sua empresa!</div>
        </div>
        <div class="card-novo">
            <h3>Cursos</h3>
            <div class="gauge" style="background: conic-gradient(#3366ff {pct_curso * 3.6}deg, #e0e0e0 0deg);"></div>
            <div class="pct">{pct_curso}%</div>
            <div class="label">das aulas concluídas</div>
            <a href="#" class="botao">Continuar Cursos</a>
            <div class="cta">Acesse suas aulas e continue seu progresso!</div>
        </div>
        <div class="card-novo">
            <h3>Saúde Empresarial</h3>
            <div class="gauge" style="background: conic-gradient(#3366ff 295deg, #e0e0e0 0deg);"></div>
            <div class="pct">{nota_saude}</div>
            <div class="label">Resultado do diagnóstico</div>
            <a href="?page=saude_empresa" class="botao">Refazer Quiz</a>
            <div class="cta">Melhore os pontos fracos da sua empresa!</div>
        </div>
        <div class="card-novo">
    <h3>Arquivos</h3>
            <div class="gauge" style="background: conic-gradient(#3366ff 0deg, #e0e0e0 0deg);"></div>
            <div class="pct">0</div>
            <div class="label">arquivos salvos</div>
            <a href="?page=arquivos" class="botao">Acessar Arquivos</a>
            <div class="cta">Organize seus documentos em um só lugar!</div>
        </div>
        <div class="card-novo">
            <h3>Agenda</h3>
            <div class="gauge" style="background: conic-gradient(#3366ff 270deg, #e0e0e0 0deg);"></div>
            <div class="pct">📅</div>
            <div class="label">Veja seus próximos compromissos</div>
            <a href="?page=agenda" class="botao">Ver Agenda</a>
            <div class="cta">Fique no controle do seu tempo!</div>
        </div>
        <div class="card-novo">
            <h3>Central de Ajuda</h3>
            <div class="gauge" style="background: conic-gradient(#3366ff 360deg, #e0e0e0 0deg);"></div>
            <div class="pct">💬</div>
            <div class="label">Precisa de ajuda?</div>
            <a href="?page=suporte" class="botao">Abrir Atendimento</a>
            <div class="cta">Estamos aqui para te apoiar no que for preciso!</div>
        </div>
    </div>
    """, unsafe_allow_html=True)




def tela_login_personalizada():
    import streamlit as st
    import httpx
    import base64
    from pathlib import Path

    global API_URL  # usa a mesma API_URL global do app

    # 🔹 Imagem de fundo da esquerda
    caminho_imagem = Path("frontend/img/telalogin.jpg")  # ou .png se for o caso
    imagem_base64 = ""
    if caminho_imagem.exists():
        with open(caminho_imagem, "rb") as f:
            imagem_base64 = base64.b64encode(f.read()).decode("utf-8")

    # 🔹 Logo em base64 (pra usar em <img> HTML, sem espaço extra do Streamlit)
    logo_path = Path("frontend/img/mivlogo preta.png")
    logo_base64 = ""
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode("utf-8")

    # 🔹 CSS geral
    st.markdown(f"""
        <style>
        * {{
            font-family: 'Segoe UI', sans-serif;
        }}

        html, body {{
            margin: 0 !important;
            padding: 0 !important;
        }}

        /* Geral: mínimo de padding possível */
        .block-container {{
            padding: 0.1rem 0.6rem 0.3rem !important;
        }}

        .left {{
            flex: 6;
            background: url("data:image/jpeg;base64,{imagem_base64}") center center no-repeat;
            background-size: cover;
            height: 100vh;
            margin: 0 !important;
            padding: 0 !important;
        }}

        .right {{
            flex: 4;
            max-width: 480px;
            margin: 0 auto;
            padding: 8px 20px !important;  /* pouco padding pra colar tudo no topo */
            background-color: white;
        }}

        /* Logo da MivCast sem margem/padding extra */
        .logo-login {{
            margin: 0 !important;
            padding: 0 !important;
            display: block;
        }}

        /* Título Login bem próximo da logo */
        h1 {{
            font-size: 32px;
            font-weight: bold;
            margin-top: -24px !important;  /* puxa o título pra cima, encostando na logo */
            margin-bottom: 2px !important;
        }}

        .subtitle {{
            color: #666;
            margin-top: 0px;
            margin-bottom: 12px;
            line-height: 1.2;
            font-size: 15px;
        }}

        /* Reduzir espaço dos textos (E-mail, Senha, etc.) */
        .right > p {{
            margin-top: 4px !important;
            margin-bottom: 4px !important;
        }}

        .stTextInput, .stPassword {{
            width: 90% !important;
            margin-bottom: 8px;
        }}

        .stTextInput > div > input,
        .stPassword > div > input {{
            padding: 10px;
            border-radius: 8px;
            border: 1px solid #ccc;
            width: 100%;
        }}

        .stButton button {{
            background-color: #265df2;
            color: white;
            font-weight: bold;
            padding: 10px;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            cursor: pointer;
            width: 100%;
        }}
        .stButton button:hover {{
            background-color: #1d47c8;
        }}

        .bottom-text {{
            font-size: 12px;
            margin-top: 6px;
            line-height: 1.2;
        }}

        /* MOBILE: espremer ao máximo e colar no topo */
        @media(max-width: 768px) {{

            .left {{
                display: none;
            }}

            .main .block-container {{
                padding-top: 0rem !important;
                padding-bottom: 0.2rem !important;
            }}

            .right {{
                flex: 1;
                width: 100% !important;
                max-width: 420px !important;
                padding: 6px 12px !important;  /* ainda menor no mobile */
                margin: 0px auto 8px !important;
                border-radius: 10px;
                box-shadow: 0 0 8px rgba(0,0,0,0.04);
            }}

            .logo-login {{
                margin: 0 !important;
                padding: 0 !important;
            }}

           h1 {{
               font-size: 24px;
               margin-top: -28px !important;   /* ainda mais colado no mobile */
               margin-bottom: 2px !important;
           }}

            .subtitle {{
                font-size: 13px;
                line-height: 1.15;
                margin-bottom: 10px !important;
            }}

            .right > p {{
                margin-top: 3px !important;
                margin-bottom: 3px !important;
            }}

            .stTextInput, .stPassword {{
                width: 100% !important;
                margin-bottom: 6px;
            }}

            .stTextInput > div > input,
            .stPassword > div > input {{
                width: 100% !important;
                padding: 8px;
            }}
        }}
        </style>
    """, unsafe_allow_html=True)

    # Layout com colunas
    col1, col2 = st.columns([6, 4])
    with col1:
        st.markdown('<div class="left"></div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="right">', unsafe_allow_html=True)

        # Logo em HTML com base64 (sem espaço extra do Streamlit)
        if logo_base64:
            st.markdown(
                f"""
                <img src="data:image/png;base64,{logo_base64}"
                     width="80"
                     class="logo-login">
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<h1>Login</h1>", unsafe_allow_html=True)
        st.markdown("<p class='subtitle'>Acesse sua conta para gerenciar seu sistema.</p>", unsafe_allow_html=True)

        st.markdown("**E-mail**")
        email = st.text_input(
            "E-mail",
            placeholder="Digite seu e-mail ou usuário",
            label_visibility="collapsed",
        )

        st.markdown("**Senha**")
        senha = st.text_input(
            "Senha",
            placeholder="Digite sua senha",
            type="password",
            label_visibility="collapsed",
        )

        # 🔐 ESQUECI MINHA SENHA
        with st.expander("Esqueci minha senha"):
            st.write("Digite o e-mail cadastrado. Enviaremos uma nova senha temporária.")

            email_rec = st.text_input(
                "Seu e-mail cadastrado",
                value=email,
                key="email_rec",
            )

            if st.button("Enviar nova senha"):
                if not email_rec.strip():
                    st.error("Informe o e-mail cadastrado.")
                else:
                    try:
                        resp = httpx.post(
                            f"{API_URL}/usuario/esqueci-senha",
                            json={"email": email_rec.strip()},
                            timeout=20.0,
                        )
                        if resp.status_code == 200:
                            msg = resp.json().get("detail", "Nova senha enviada para o seu e-mail.")
                            st.success(msg)
                        else:
                            detalhe = ""
                            try:
                                detalhe = resp.json().get("detail", "")
                            except Exception:
                                pass
                            if detalhe:
                                st.error(detalhe)
                            else:
                                st.error(f"Erro ao enviar nova senha ({resp.status_code}).")
                    except Exception as e:
                        st.error(f"Erro de conexão: {e}")

        # 🔹 Botão de login
        if st.button("Acessar meu Sistema", use_container_width=True):
            login_usuario(email, senha)

        st.markdown("Ainda não tem cadastro na MivCast?")

        if st.button("📩 Cadastre-se agora", use_container_width=True):
            st.query_params = {"cadastro": "true"}
            st.rerun()

        st.markdown("""
        <p class="bottom-text">
        🆓 <b>Teste 03 dias GRÁTIS </b>o Plano Profissional
        </p>
        """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)









def login_usuario(email, senha):
    """Realiza login e retorna o token"""
    try:
        response = httpx.post(
            f"{API_URL}/login",
            data={"username": email, "password": senha},
            timeout=15.0,
        )

        if response.status_code == 200:
            token = response.json().get("access_token")
            if not token:
                st.error("Resposta do servidor sem token de acesso.")
                return

            st.session_state["token"] = token
            obter_dados_usuario()  # já puxa os dados do usuário
            st.success("✅ Login realizado com sucesso!")
            st.rerun()

        elif response.status_code == 404:
            # E-mail não cadastrado
            st.error("Este e-mail ainda **não está cadastrado**. Clique em *Criar sua conta* para se registrar.")

        elif response.status_code == 401:
            # Senha incorreta
            st.error("Senha incorreta. Verifique e tente novamente.")

        else:
            # Outros erros (500, 422, etc.)
            detalhe = ""
            try:
                detalhe_json = response.json()
                detalhe = detalhe_json.get("detail", "")
            except Exception:
                pass

            if detalhe:
                st.error(f"Erro ao fazer login ({response.status_code}): {detalhe}")
            else:
                st.error(f"Erro ao fazer login ({response.status_code}).")

    except Exception as e:
        st.error(f"Erro ao fazer login: {e}")



# ------------------- FUNÇÕES DE APOIO DO USUÁRIO -------------------


def obter_dados_usuario():
    """Consulta os dados do usuário logado e guarda em st.session_state"""
    try:
        response = httpx.get(f"{API_URL}/minha-conta", headers=get_headers())
        if response.status_code == 200:
            st.session_state["dados_usuario"] = response.json()
        else:
            st.error("Erro ao obter dados do usuário.")
            st.session_state["token"] = None
    except Exception as e:
        st.error(f"Erro ao consultar perfil: {e}")




# ------------------- CADASTRO (VERSÃO CORRETA) -------------------
def tela_cadastro():
    import streamlit as st
    import httpx

    # ======================================================
    # CONFIG
    # ======================================================
    API_URL = (st.session_state.get("API_URL") or "").strip().rstrip("/")
    if not API_URL:
        st.error("API_URL não definido em st.session_state['API_URL'].")
        st.stop()

    st.title("📝 Criar sua conta")
    st.caption(
        "Crie sua conta em menos de 1 minuto. Você terá **3 dias de acesso de teste** para conhecer o sistema. "
        "Depois, é só escolher seu plano na aba **Planos**."
    )

    # ======================================================
    # STATE
    # ======================================================
    if "cad_ok" not in st.session_state:
        st.session_state["cad_ok"] = False

    def _safe_detail(resp: httpx.Response) -> str:
        try:
            j = resp.json() or {}
            return j.get("detail") or resp.text
        except Exception:
            return resp.text or "Resposta vazia do servidor."

    # ======================================================
    # UI
    # ======================================================
    st.markdown("### 📋 Dados da sua conta")

    with st.form("form_cadastro_simples"):
        nome = st.text_input("Nome completo", placeholder="Ex: Matheus Nascimento")
        email = st.text_input("E-mail", placeholder="Ex: seuemail@gmail.com")
        senha = st.text_input("Senha", type="password", placeholder="Crie uma senha")
        confirmar = st.text_input("Confirmar senha", type="password", placeholder="Digite a senha novamente")

        st.markdown(
            """
            <div style="background:#fff3cd; border:1px solid #ffeeba; padding:12px; border-radius:10px; margin-top:10px;">
                <strong>🔔 Importante:</strong> Após criar sua conta, você poderá acessar o sistema por <strong>3 dias</strong>.
                Dentro do app, vá em <strong>Menu → Planos</strong> para escolher o plano ideal e liberar o acesso completo.
            </div>
            """,
            unsafe_allow_html=True,
        )

        criar = st.form_submit_button("✅ Criar conta")

    # ======================================================
    # SUBMIT
    # ======================================================
    if criar:
        nome = (nome or "").strip()
        email = (email or "").strip().lower()
        senha = senha or ""
        confirmar = confirmar or ""

        if not nome or not email or not senha or not confirmar:
            st.error("Preencha todos os campos.")
            st.stop()

        if senha != confirmar:
            st.error("As senhas não coincidem.")
            st.stop()

        # cria a conta (sempre cadastro-gratuito)
        try:
            resp = httpx.post(
                f"{API_URL}/usuario/cadastro-gratuito",
                json={"nome": nome, "email": email, "senha": senha},
                timeout=30,
            )
        except Exception as e:
            st.error(f"Erro ao conectar no cadastro: {e}")
            st.stop()

        if resp.status_code != 200:
            st.error(f"❌ Erro ao cadastrar ({resp.status_code}): {_safe_detail(resp)}")
            st.stop()

        st.session_state["cad_ok"] = True
        st.session_state["cad_email"] = email
        st.rerun()

    # ======================================================
    # PÓS-CADASTRO
    # ======================================================
    if st.session_state.get("cad_ok"):
        st.success("✅ Conta criada com sucesso!")

        st.info(
            "Agora faça login com seu e-mail e senha.\n\n"
            "Assim que entrar, vá em **Menu → Planos** e escolha o plano ideal para liberar o acesso completo."
        )

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔑 Ir para login"):
                st.query_params = {"login": "true"}
                st.rerun()

        with c2:
            if st.button("➕ Criar outra conta"):
                st.session_state["cad_ok"] = False
                st.session_state.pop("cad_email", None)
                st.rerun()

    st.markdown("---")
    if st.button("🔑 Já tenho conta? Ir para login"):
        st.query_params = {"login": "true"}
        st.rerun()




# ------------------- SETORES -------------------

def setor_acesso(nome_setor, titulo, conteudo):
    st.header(titulo)
    st.info(conteudo)





def tela_empresa():
    st.header("🏢 Dados da Empresa")

    from pathlib import Path
    import base64

    def carregar_imagem_base64(caminho):
        with open(caminho, "rb") as f:
            return base64.b64encode(f.read()).decode()

    CAMINHO_AVATAR = Path(__file__).parent / "img" / "avatar.jpeg"
    avatar_base64 = carregar_imagem_base64(CAMINHO_AVATAR)

    st.markdown(f"""
    <div style="background-color:#d0e7fe; border-left: 6px solid #0f00ff; padding: 20px; border-radius: 10px; margin-bottom: 30px;">
        <div style="display: flex; align-items: center;">
            <img src="data:image/jpeg;base64,{avatar_base64}" alt="MARK IA" width="100" style="margin-right: 15px; border-radius: 50%;">
            <div>
                <h3 style="margin-bottom: 5px;">📋 Bem-vindo ao módulo <strong>Dados da Empresa</strong></h3>
                <p style="margin: 0; color: #333;">
                    Aqui é onde tudo começa! Preencha os dados principais da sua empresa para que o sistema possa personalizar sua experiência.
                </p>
                <p style="margin: 0; margin-top: 10px; color: #555;">
                    ➕ <strong>Dica do MARK:</strong> Quanto mais detalhada for a descrição da sua empresa, melhor será o desempenho da IA em todos os módulos.
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # -------- Carregar dados da API --------
    dados = {}
    try:
        r = httpx.get(f"{API_URL}/empresa", headers=get_headers())
        if r.status_code == 200:
            dados = r.json()
    except Exception:
        st.warning("Erro ao buscar dados da empresa.")

    # 🔹 Nome da empresa (variável exclusiva)
    nome_empresa = st.text_input("Nome da Empresa", value=dados.get("nome_empresa", ""))
    descricao_empresa = st.text_area("Descrição", value=dados.get("descricao", ""))
    nicho = st.text_input("Nicho", value=dados.get("nicho", ""))

    # 🖼 Logo
    st.markdown("#### 🖼 Logo da Empresa")
    logo_url = st.text_input("URL da Logo", value=dados.get("logo_url", ""))
    logo_upload = st.file_uploader("Ou envie a imagem (PNG ou JPG)", type=["png", "jpg", "jpeg"])
    if logo_upload:
        conteudo = logo_upload.read()
        logo_url = f"data:image/png;base64,{base64.b64encode(conteudo).decode()}"
    if logo_url:
        st.image(logo_url, caption="Pré-visualização da Logo", width=150)

    # 🗺 Endereço
    st.markdown("#### 🗺 Endereço Completo")
    cnpj = st.text_input("CNPJ", value=dados.get("cnpj", ""))
    col1, col2 = st.columns(2)
    with col1:
        rua = st.text_input("Rua / Avenida", value=dados.get("rua", ""))
        numero = st.text_input("Número", value=dados.get("numero", ""))
        bairro = st.text_input("Bairro", value=dados.get("bairro", ""))
    with col2:
        cidade = st.text_input("Cidade", value=dados.get("cidade", ""))
        cep = st.text_input("CEP", value=dados.get("cep", ""))

    # 👥 Funcionários
    st.markdown("#### 👥 Funcionários")
    if "lista_funcionarios" not in st.session_state:
        st.session_state.lista_funcionarios = dados.get("funcionarios", [])
    if "funcionario_em_edicao" not in st.session_state:
        st.session_state.funcionario_em_edicao = None

    for i, f in enumerate(st.session_state.lista_funcionarios):
        titulo = f"👤 {f.get('nome', '')} - {f.get('funcao', '')}" if f.get("nome") else f"👤 Funcionário {i+1}"
        with st.expander(titulo, expanded=st.session_state.funcionario_em_edicao == i):
            func_nome = st.text_input("Nome", value=f.get("nome", ""), key=f"func_nome_{i}")
            nasc = st.text_input("Data de Nascimento", value=f.get("data_nascimento", ""), key=f"func_nasc_{i}")
            funcao = st.text_input("Função", value=f.get("funcao", ""), key=f"func_funcao_{i}")
            tel = st.text_input("Telefone", value=f.get("telefone", ""), key=f"func_tel_{i}")
            obs = st.text_area("Observação", value=f.get("observacao", ""), key=f"func_obs_{i}")
            colsalva, colexc = st.columns(2)
            with colsalva:
                if st.button("💾 Salvar", key=f"salvar_func_{i}"):
                    f.update({
                        "nome": func_nome,
                        "data_nascimento": nasc,
                        "funcao": funcao,
                        "telefone": tel,
                        "observacao": obs
                    })
                    st.session_state.funcionario_em_edicao = None
                    st.rerun()
            with colexc:
                if st.button("🗑 Excluir", key=f"excluir_func_{i}"):
                    st.session_state.lista_funcionarios.pop(i)
                    st.session_state.funcionario_em_edicao = None
                    st.rerun()

    if st.button("➕ Adicionar Funcionário"):
        st.session_state.lista_funcionarios.append({
            "nome": "",
            "data_nascimento": "",
            "funcao": "",
            "telefone": "",
            "observacao": ""
        })
        st.session_state.funcionario_em_edicao = len(st.session_state.lista_funcionarios) - 1
        st.rerun()

    # 🛍 Produtos
    st.markdown("#### 🛍 Produtos")
    if "lista_produtos" not in st.session_state:
        st.session_state.lista_produtos = dados.get("produtos", [])
    if "produto_em_edicao" not in st.session_state:
        st.session_state.produto_em_edicao = None

    for i, p in enumerate(st.session_state.lista_produtos):
        titulo = f"📦 {p.get('nome', '')}" if p.get("nome") else f"📦 Produto {i+1}"
        with st.expander(titulo, expanded=st.session_state.produto_em_edicao == i):
            prod_nome = st.text_input("Nome do Produto", value=p.get("nome", ""), key=f"prod_nome_{i}")
            preco_val = p.get("preco", 0.0) or 0.0
            preco = st.number_input("Preço", value=float(preco_val), key=f"prod_preco_{i}", min_value=0.0)
            descricao = st.text_area("Descrição", value=p.get("descricao", ""), key=f"prod_desc_{i}")
            imagem = st.text_input("Imagem (URL ou base64)", value=p.get("imagem", ""), key=f"prod_img_url_{i}")
            upload = st.file_uploader("Ou envie a imagem do produto", type=["png", "jpg", "jpeg"], key=f"prod_upload_{i}")
            if upload:
                conteudo = upload.read()
                imagem = f"data:image/png;base64,{base64.b64encode(conteudo).decode()}"
            if imagem:
                st.image(imagem, width=200)
            colsalva, colexc = st.columns(2)
            with colsalva:
                if st.button("💾 Salvar", key=f"salvar_prod_{i}"):
                    p.update({
                        "nome": prod_nome,
                        "preco": preco,
                        "descricao": descricao,
                        "imagem": imagem
                    })
                    st.session_state.produto_em_edicao = None
                    st.rerun()
            with colexc:
                if st.button("🗑 Excluir", key=f"excluir_prod_{i}"):
                    st.session_state.lista_produtos.pop(i)
                    st.session_state.produto_em_edicao = None
                    st.rerun()

    if st.button("➕ Adicionar Produto"):
        st.session_state.lista_produtos.append({
            "nome": "",
            "preco": 0.0,
            "descricao": "",
            "imagem": ""
        })
        st.session_state.produto_em_edicao = len(st.session_state.lista_produtos) - 1
        st.rerun()

    # 🌐 Redes Sociais
    st.markdown("#### 🌐 Redes Sociais")
    redes = dados.get("redes_sociais", {})
    instagram = st.text_input("Instagram", value=redes.get("instagram", ""))
    whatsapp = st.text_input("WhatsApp", value=redes.get("whatsapp", ""))
    facebook = st.text_input("Facebook", value=redes.get("facebook", ""))
    tiktok = st.text_input("TikTok", value=redes.get("tiktok", ""))
    youtube = st.text_input("YouTube", value=redes.get("youtube", ""))

    adicionais = st.text_area("Informações Adicionais", value=dados.get("informacoes_adicionais", ""))

    # 🔘 Salvar Empresa
    if st.button("Salvar Empresa"):
        payload = {
            "nome_empresa": nome_empresa,  # <- AGORA CERTO
            "descricao": descricao_empresa,
            "nicho": nicho,
            "logo_url": logo_url,
            "cnpj": cnpj,
            "rua": rua,
            "numero": numero,
            "bairro": bairro,
            "cidade": cidade,
            "cep": cep,
            "funcionarios": st.session_state.lista_funcionarios,
            "produtos": st.session_state.lista_produtos,
            "redes_sociais": {
                "instagram": instagram,
                "whatsapp": whatsapp,
                "facebook": facebook,
                "tiktok": tiktok,
                "youtube": youtube
            },
            "informacoes_adicionais": adicionais
        }

        # 🔎 DEBUG (pode remover depois)
        # st.write("DEBUG payload_enviado:", payload)

        try:
            r = httpx.post(f"{API_URL}/empresa", json=payload, headers=get_headers())
            # st.write("DEBUG status_code:", r.status_code, "body:", r.text)
            if r.status_code == 200:
                st.success("✅ Empresa salva com sucesso!")
            else:
                st.error("Erro ao salvar empresa.")
                st.error(r.text)
        except Exception as e:
            st.error(f"Erro inesperado: {e}")





def tela_consultoria():
    # ⚠️ Verificação de acesso: Admin sempre tem acesso total
    email_usuario = st.session_state.get("dados_usuario", {}).get("email", "")
    if email_usuario != "matheus@email.com":
        if not usuario_tem_acesso("consultoria"):
            mostrar_bloqueio_modulo("Consultoria Interativa")
            st.stop()

    import json
    import datetime

    st.title("📋 Consultoria Interativa")

    # ✅ Bloco com guia visual do MARK com avatar personalizado
    from pathlib import Path
    import base64

    def carregar_imagem_base64(caminho):
        with open(caminho, "rb") as f:
            return base64.b64encode(f.read()).decode()

    CAMINHO_AVATAR = Path(__file__).parent / "img" / "avatar.jpeg"
    avatar_base64 = carregar_imagem_base64(CAMINHO_AVATAR)

    st.markdown(f"""
    <div style="background-color:#d0e7fe; border-left: 6px solid #0f00ff; padding: 20px; border-radius: 10px; margin-bottom: 30px;">
        <div style="display: flex; align-items: center;">
            <img src="data:image/jpeg;base64,{avatar_base64}" alt="MARK IA" width="100" style="margin-right: 15px; border-radius: 50%;">
            <div>
                <h3 style="margin-bottom: 5px;">📊 Consultoria Interativa MivCast</h3>
                <p style="margin: 0; color: #333;">
                    Aqui você terá acesso ao método exclusivo da MivCast para diagnosticar, organizar e melhorar sua empresa em 63 tópicos estratégicos.
                        Marque os checklists, faça anotações e veja seu progresso. Você pode seguir a ordem sugerida ou escolher por setor.
                </p>
                <p style="margin: 0; margin-top: 10px; color: #555;">
                    ✅ <strong>Dica do MARK:</strong> Use esse módulo semanalmente. Ao finalizar, você terá um plano completo para crescer com mais clareza.
                </p>
                </div>
        </div>
    </div>
""", unsafe_allow_html=True)


    if not st.session_state.token:
        st.warning("Você precisa estar logado para acessar.")
        return

    headers = get_headers()

    try:
        r = httpx.get(f"{API_URL}/consultoria", headers=headers)
        if r.status_code == 404:
            criar = httpx.post(f"{API_URL}/consultoria/iniciar", headers=headers)
            if criar.status_code != 200:
                st.error("Erro ao iniciar consultoria.")
                return
    except Exception as e:
        st.error(f"Erro ao verificar consultoria: {e}")
        return

    try:
        with open("data/consultoria_topicos_completos.json", "r", encoding="utf-8") as f:
            topicos = json.load(f)
        with open("data/topicos_por_setor.json", "r", encoding="utf-8") as f:
            por_setor = json.load(f)
    except Exception as e:
        st.error(f"Erro ao carregar arquivos de tópicos: {e}")
        return

    try:
        r = httpx.get(f"{API_URL}/consultoria/progresso", headers=headers)
        progresso = r.json() if r.status_code == 200 else {}
    except Exception as e:
        st.error(f"Erro ao buscar progresso: {e}")
        progresso = {}

    if "consultoria_alterado" not in st.session_state:
        st.session_state.consultoria_alterado = False

    for t in topicos:
        tid = str(t["id"])
        if tid not in progresso:
            progresso[tid] = {
                "checklist": [False] * len(t["checklist"]),
                "concluido": False,
                "comentario": "",
                "favorito": False,
                "prioridade": "Média",
                "atualizado_em": datetime.datetime.now().isoformat()
            }
        else:
            progresso[tid].setdefault("comentario", "")
            progresso[tid].setdefault("favorito", False)
            progresso[tid].setdefault("prioridade", "Média")
            progresso[tid].setdefault("atualizado_em", datetime.datetime.now().isoformat())

    total = len(topicos)
    concluidos = sum(1 for t in topicos if progresso[str(t["id"])]["concluido"])
    porcentagem = int((concluidos / total) * 100) if total > 0 else 0

    st.markdown("### 📈 Progresso da Consultoria")
    st.progress(porcentagem / 100)
    st.success(f"{concluidos} de {total} tópicos concluídos ({porcentagem}%)")
    st.markdown("---")

    modo = st.radio("🔎 Como deseja estudar?", ["Ordem Estratégica", "Por Setor"], horizontal=True)
    filtro = st.radio("🎯 Filtro:", ["Todos", "Pendentes", "Favoritos", "Alta Prioridade"], horizontal=True)

    def exibir_topico(t):
        tid = str(t["id"])
        dados = progresso[tid]
        if filtro == "Pendentes" and dados["concluido"]:
            return
        if filtro == "Favoritos" and not dados["favorito"]:
            return
        if filtro == "Alta Prioridade" and dados["prioridade"] != "Alta":
            return

        st.markdown(f"### {t['id']}. {t['titulo']}")
        st.write(t["descricao"])

        for i, item in enumerate(t["checklist"]):
            key = f"chk_{tid}_{i}"
            novo_valor = st.checkbox(item, value=dados["checklist"][i], key=key)
            if novo_valor != dados["checklist"][i]:
                dados["checklist"][i] = novo_valor
                dados["atualizado_em"] = datetime.datetime.now().isoformat()
                st.session_state.consultoria_alterado = True

        dados["concluido"] = all(dados["checklist"])

        st.selectbox("📌 Prioridade", ["Alta", "Média", "Baixa"], key=f"prioridade_{tid}", index=["Alta", "Média", "Baixa"].index(dados["prioridade"]), on_change=lambda: atualizar_prioridade(dados, tid))
        dados["favorito"] = st.checkbox("⭐ Marcar como favorito", value=dados["favorito"], key=f"fav_{tid}")
        dados["comentario"] = st.text_area("📝 Comentário", value=dados["comentario"], key=f"obs_{tid}", height=80)
        st.caption(f"📆 Última atualização: {datetime.datetime.fromisoformat(dados['atualizado_em']).strftime('%d/%m/%Y %H:%M')}")
        st.success("✅ Concluído" if dados["concluido"] else "🔲 Em andamento")
        st.divider()

    def atualizar_prioridade(dados, tid):
        dados["prioridade"] = st.session_state[f"prioridade_{tid}"]
        dados["atualizado_em"] = datetime.datetime.now().isoformat()
        st.session_state.consultoria_alterado = True

    if modo == "Ordem Estratégica":
        for t in topicos:
            exibir_topico(t)
    else:
        setor = st.selectbox("Selecione o setor:", list(por_setor.keys()))
        for t in topicos:
            if t["id"] in por_setor.get(setor, []):
                exibir_topico(t)

    if st.session_state.consultoria_alterado:
        try:
            r = httpx.put(f"{API_URL}/consultoria/progresso", headers=headers, json={"progresso": progresso})
            if r.status_code == 200:
                st.success("📝 Progresso salvo automaticamente!")
                st.session_state.consultoria_alterado = False
            else:
                st.warning("⚠️ Houve erro ao salvar progresso.")
        except Exception as e:
            st.error(f"Erro ao conectar com o servidor: {e}")

    if st.button("💾 Salvar progresso manualmente"):
        try:
            r = httpx.put(f"{API_URL}/consultoria/progresso", headers=headers, json={"progresso": progresso})
            if r.status_code == 200:
                st.success("✅ Progresso salvo com sucesso!")
            else:
                st.error(f"Erro ao salvar: {r.text}")
        except Exception as e:
            st.error(f"Erro ao conectar com o servidor: {e}")

    resumo = "\n".join([
        f"{t['id']}. {t['titulo']} - {'✅ Concluído' if progresso[str(t['id'])]['concluido'] else '🔲 Pendente'}"
        for t in topicos
    ])
    st.download_button("📥 Exportar resumo (.txt)", data=resumo, file_name="resumo_consultoria.txt", mime="text/plain")


def exibir_carrossel(titulo, lista, tipo_chave):
    st.markdown(f"## {titulo}")
    if not lista:
        st.info("Nenhum card disponível.")
        return

    html = """
    <style>
        .grid-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 16px;
            padding: 10px 20px;
        }
        .card {
            background-color: #fff;
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            height: 100%;
        }
        .atualizacao {
            background-color: #0066cc;
            color: white;
            font-size: 12px;
            padding: 4px 8px;
            border-radius: 4px;
            display: inline-block;
            margin-bottom: 6px;
        }
        .card h4 {
            margin: 6px 0 4px;
            font-size: 16px;
        }
        .card small {
            color: #888;
            font-size: 12px;
        }
        .card a {
            color: #0066cc;
            font-size: 13px;
        }
        .card ol {
            font-size: 13px;
            padding-left: 18px;
            margin: 6px 0;
        }
        .favorito {
            color: #aaa;
            font-size: 14px;
            margin-top: 8px;
        }
    </style>
    <div class="grid-container">
    """

    for card in lista:
        html += f"""
        <div class="card">
            {"<div class='atualizacao'>🆕 Atualização recente!</div>" if card.get("eh_atualizacao") else ""}
            <h4>📌 {card['titulo']}</h4>
            <small>🕒 {card['atualizado_em'][:10]}</small>
            <p>{card['descricao']}</p>
            <a href="{card['fonte']}" target="_blank">🔗 Fonte original</a>
            <p><strong>💡 Ideias de conteúdo:</strong></p>
            <ol>
        """

        for ideia in card["ideias_conteudo"].splitlines():
            if ideia.strip():
                html += f"<li>{ideia.strip()}</li>"

        favorito = "⭐" if card.get("favorito") else "☆"
        html += f"""
            </ol>
            <div class="favorito">{favorito} Favoritar (clique desativado)</div>
        </div>
        """

    html += "</div>"

    components.html(html, height=800 + (len(lista) // 5 * 160), scrolling=True)



def tela_consultor_mensal():
    import datetime
    import httpx
    import streamlit as st

    st.title("🧠 Consultor Mensal de Marketing & Branding")
    st.caption("Estratégia clara, ideias prontas e orientação prática.")

    if not st.session_state.get("token"):
        st.warning("Você precisa estar logado para acessar.")
        return

    headers = get_headers()

    # Puxa empresa atual
    try:
        r = httpx.get(f"{API_URL}/empresa", headers=headers, timeout=30)
        if r.status_code != 200:
            st.error("Não consegui carregar a empresa (endpoint /empresa).")
            st.stop()
        empresa = r.json()
    except Exception as e:
        st.error(f"Erro ao buscar empresa: {e}")
        st.stop()

    # IMPORTANTE: não assumir id sempre
    empresa_id = empresa.get("id") or empresa.get("empresa_id")
    if not empresa_id:
        st.error("Sua empresa não retornou o campo 'id'. Ajuste o /empresa para incluir 'id'.")
        st.stop()

    mes_padrao = datetime.datetime.now().strftime("%Y-%m")
    mes_ano = st.text_input("📅 Mês (YYYY-MM)", value=mes_padrao)

    colA, colB = st.columns([1, 1])
    with colA:
        if st.button("✨ Gerar consultoria do mês", type="primary"):
            try:
                rr = httpx.post(f"{API_URL}/consultor-mensal/gerar/{empresa_id}/{mes_ano}", headers=headers, timeout=120)
                if rr.status_code == 200:
                    st.success("Consultoria gerada com sucesso.")
                    st.rerun()
                else:
                    st.error(rr.text)
            except Exception as e:
                st.error(f"Erro ao gerar: {e}")

    with colB:
        if st.button("🔁 Gerar nova versão do mês"):
            try:
                rr = httpx.post(f"{API_URL}/consultor-mensal/regerar/{empresa_id}/{mes_ano}", headers=headers, timeout=120)
                if rr.status_code == 200:
                    st.success("Nova versão gerada e salva.")
                    st.rerun()
                else:
                    st.error(rr.text)
            except Exception as e:
                st.error(f"Erro ao regerar: {e}")

    st.divider()

    # GET do mês
    try:
        r = httpx.get(f"{API_URL}/consultor-mensal/{empresa_id}/{mes_ano}", headers=headers, timeout=60)
        if r.status_code == 404:
            st.info("Nenhuma consultoria gerada para este mês.")
            return
        if r.status_code != 200:
            st.error(r.text)
            return
        conteudo = r.json().get("conteudo") or {}
    except Exception as e:
        st.error(f"Erro ao buscar consultoria: {e}")
        return

    # Nunca usar conteudo["chave"] direto
    st.subheader("📌 Resumo Estratégico")
    st.write(conteudo.get("resumo_executivo", "Resumo não disponível (backend não enviou)."))

    st.caption(
        f"Empresa: {conteudo.get('empresa_nome', empresa.get('nome_empresa',''))} | "
        f"Nicho: {conteudo.get('nicho', empresa.get('nicho',''))} | "
        f"Mês: {conteudo.get('mes_ano', mes_ano)} | "
        f"Versão: {conteudo.get('versao', 1)}"
    )

    st.divider()

    blocos = conteudo.get("blocos", [])
    if not blocos:
        st.warning("Nenhum bloco encontrado na consultoria.")
        return

    for bloco in blocos:
        titulo = bloco.get("titulo", "Tema")
        intro = bloco.get("intro", "")
        conteudos = bloco.get("conteudos", [])
        branding = bloco.get("branding", [])

        with st.expander(titulo, expanded=False):
            if intro:
                st.info(intro)

            st.markdown("### 💡 Ideias de Conteúdo")
            if not conteudos:
                st.write("Nenhuma ideia de conteúdo.")
            else:
                for item in conteudos:
                    st.markdown(f"**{item.get('numero','')}º Ideia:** {item.get('assunto','')}")
                    st.markdown(f"🖼️ **Imagem:** {item.get('criativo_imagem','')}")
                    st.markdown(f"🎥 **Vídeo:** {item.get('criativo_video','')}")
                    st.markdown("✍️ **Legenda pronta para copiar:**")
                    st.code(item.get("legenda",""))

                    st.markdown("---")

            st.markdown("### 🧠 Dicas de Branding")
            if not branding:
                st.write("Nenhuma dica de branding.")
            else:
                for dica in branding:
                    st.markdown(f"**{dica.get('numero','')}º Dica:** {dica.get('texto','')}")
















def tela_arquivos():
    # ⚠️ Verificação de acesso: Admin sempre tem acesso total
    email_usuario = st.session_state.get("dados_usuario", {}).get("email", "")
    if email_usuario != "matheus@email.com":
        if not usuario_tem_acesso("arquivo"):
            mostrar_bloqueio_modulo("Central de Arquivos")
            st.stop()

    import base64
    from pathlib import Path
    import os

    setor_acesso("arquivos", "📁 Arquivos", "(Conteúdo dos arquivos aqui)")

    def carregar_imagem_base64(caminho):
        with open(caminho, "rb") as f:
            return base64.b64encode(f.read()).decode()

    CAMINHO_AVATAR = Path(__file__).parent / "img" / "avatar.jpeg"
    avatar_base64 = carregar_imagem_base64(CAMINHO_AVATAR)

    st.markdown(f"""
    <div style="background-color:#d0e7fe; border-left: 6px solid #0f00ff; padding: 20px; border-radius: 10px; margin-bottom: 30px;">
        <div style="display: flex; align-items: center;">
            <img src="data:image/jpeg;base64,{avatar_base64}" alt="MARK IA" width="100" style="margin-right: 15px; border-radius: 50%;">
            <div>
                <h3 style="margin-bottom: 5px;">📁 Central de Arquivos Inteligente</h3>
                <p style="margin: 0; color: #333;">
                    Aqui você pode guardar, visualizar ou compartilhar arquivos importantes da sua empresa: contratos, imagens, PDFs, comprovantes, e muito mais.
                </p>
                <p style="margin: 0; margin-top: 10px; color: #555;">
                    📎 <strong>Dica do MARK:</strong> Use nomes claros e organize os arquivos corretamente. Em breve poderei interpretar os documentos para te ajudar!
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Pastas padrão
    BASE_ARQUIVOS = Path("data/arquivos_usuario")
    PASTAS = [
        "Logo e Documentos da Logo",
        "Documentos Jurídicos",
        "Comprovantes",
        "Contratos e Propostas",
        "Documentos Diversos",
        "Identidade Visual",
        "Notas Fiscais",
        "Recibos e Boletos"
    ]

    for pasta in PASTAS:
        st.markdown(f"### 📂 {pasta}")
        caminho = BASE_ARQUIVOS / pasta
        caminho.mkdir(parents=True, exist_ok=True)

        # Upload
        arquivos = st.file_uploader(f"Enviar arquivos para '{pasta}'", accept_multiple_files=True, key=f"upload_{pasta}")
        for arquivo in arquivos:
            destino = caminho / arquivo.name
            with open(destino, "wb") as f:
                f.write(arquivo.read())
            st.success(f"✅ {arquivo.name} enviado com sucesso!")

        # Lista arquivos existentes
        arquivos_existentes = list(caminho.glob("*"))
        if arquivos_existentes:
            for arq in arquivos_existentes:
                col1, col2, col3 = st.columns([5, 2, 1])
                with col1:
                    if arq.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                        st.image(str(arq), width=200)
                    else:
                        st.markdown(f"📄 **{arq.name}**")

                with col2:
                    with open(arq, "rb") as f:
                        st.download_button("⬇️ Baixar", data=f.read(), file_name=arq.name, mime="application/octet-stream", key=f"baixar_{pasta}_{arq.name}")

                with col3:
                    if st.button("🗑️", key=f"excluir_{pasta}_{arq.name}"):
                        try:
                            arq.unlink()
                            st.success(f"{arq.name} excluído.")
                            st.rerun()
                        except:
                            st.error("Erro ao excluir.")
        else:
            st.caption("Nenhum arquivo nesta categoria ainda.")
        st.divider()



def tela_mark_ia():
    import os
    import streamlit as st
    import streamlit.components.v1 as components
    import httpx  # garantir que httpx está disponível

    # 🔹 Pega o ID do usuário logado (se tiver)
    dados_usuario = st.session_state.get("dados_usuario", {}) or {}
    usuario_id = dados_usuario.get("id", None)

    # 🔹 Lê o HTML do chat
    caminho_html = os.path.join("frontend", "mark_chat.html")
    try:
        with open(caminho_html, "r", encoding="utf-8") as f:
            html = f.read()
    except FileNotFoundError:
        st.error(f"Arquivo não encontrado: {caminho_html}")
        return

    # 🔹 Injeta o ID do usuário dentro do HTML
    html = html.replace("{{USUARIO_ID}}", str(usuario_id or ""))

    # 🔹 CSS global para o iframe do MARK usar quase toda a tela
    st.markdown(
        """
        <style>
          /* Desktop / notebooks grandes */
          iframe[srcdoc*="MARK.IA Chat"] {
              width: 100% !important;
              height: calc(100vh - 280px) !important;
              border: none;
              border-radius: 24px;
              box-shadow: 0 18px 40px rgba(15, 23, 42, 0.16);
          }

          /* Tablets e notebooks menores */
          @media (max-width: 1100px) and (min-width: 769px) {
              iframe[srcdoc*="MARK.IA Chat"] {
                  height: calc(100vh - 260px) !important;
              }
          }

          /* Celulares em geral */
          @media (max-width: 768px) {
              iframe[srcdoc*="MARK.IA Chat"] {
                  height: calc(100vh - 240px) !important;
                  border-radius: 18px;
              }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 🔹 Renderiza o chat
    components.html(
        html,
        height=650,
        scrolling=False,
    )

    # 🔹 Texto de apoio abaixo do chat
    st.markdown(
        """
        ### Como usar o MARK IA

        - Digite sua dúvida na caixa de mensagem do chat acima.  
        - Clique no botão de **microfone** para falar em vez de digitar (quando disponível).  
        - Use o botão de **limpar conversa** para começar um novo assunto.  

        Caso alguma parte do layout fique um pouquinho cortada em algum dispositivo,
        é porque logo abaixo do chat ficam estas instruções e textos de apoio.
        """
    )


    # ===============================
    # 🔎 BUSCA NO HISTÓRICO DO MARK
    # ===============================

    st.subheader("🔍 Buscar no histórico")

    termo_busca = st.text_input(
        "Digite uma palavra, frase ou parte da data:",
        placeholder="Ex.: Google Ads, orçamento, Instagram..."
    ).strip()

    params = {}
    if termo_busca:
        params["busca"] = termo_busca

    # 🔐 Cabeçalho com token (se existir)
    token = st.session_state.get("access_token", "")
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Sempre inicializa a lista
    registros = []

    try:
        r_hist = httpx.get(
            f"{API_URL}/mark/historico_v2",
            params=params,
            headers=headers or None,   # se estiver vazio, manda None
            timeout=30,
        )

        if r_hist.status_code == 200:
            registros = r_hist.json()

            if not registros:
                if termo_busca:
                    st.info("Nenhum registro encontrado para essa busca.")
                else:
                    st.info("Nenhuma interação registrada ainda.")
            else:
                st.markdown("---")

                for h in registros:
                    data = h.get("data_envio") or ""
                    remetente = h.get("remetente", "").capitalize()
                    mensagem = h.get("mensagem", "")

                    st.markdown(f"### 🕒 {data}")
                    st.markdown(f"**{remetente}:** {mensagem}")
                    st.markdown("---")

        else:
            st.error(f"Erro ao carregar histórico: {r_hist.status_code}")

    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")


    # =====================================
    # 📤 EXPORTAR HISTÓRICO COMO .TXT
    # =====================================

    if registros:
        conteudo_txt = "\n\n".join(
            [
                f"{h.get('data_envio', '')} - {h.get('remetente', '').capitalize()}: {h.get('mensagem', '')}"
                for h in registros
            ]
        )

        st.download_button(
            "📤 Exportar histórico (.txt)",
            data=conteudo_txt,
            file_name="historico_mark.txt",
            mime="text/plain",
        )





    # ===============================
    # BLOCO: Histórico abaixo do chat
    # ===============================
    st.markdown("---")
    st.markdown("### 🧠 Histórico de Conversas com o MARK")

    # ❌ Sem header Authorization aqui
    try:
        r = httpx.get(f"{API_URL}/mark/historico_v2", timeout=10.0)
        if r.status_code == 200:
            historico_total = r.json()
        else:
            st.warning(f"Não foi possível carregar o histórico (status {r.status_code}).")
            historico_total = []
    except Exception as e:
        st.error(f"Erro ao buscar histórico: {e}")
        historico_total = []

    # 🔹 Filtra só do usuário logado (se tiver ID)
    if usuario_id:
        historico = [
            h for h in historico_total
            if h.get("usuario_id") == usuario_id
        ]
    else:
        historico = historico_total

    # Exibição formatada
    if not historico:
        st.info("Nenhuma conversa registrada ainda.")
    else:
        historico = sorted(
            historico,
            key=lambda x: (x.get("data_envio") or ""),
            reverse=True,
        )

        for item in historico:
            remetente_raw = (item.get("remetente") or "").lower()
            remetente = "Você" if remetente_raw == "usuário" else "MARK IA"
            mensagem = item.get("mensagem", "")
            data = item.get("data_envio", "") or ""
            if data:
                data = data.replace("T", " ").split(".")[0]

            st.markdown(
                f"""
                <div style="
                    margin-bottom: 12px;
                    padding: 12px;
                    border-radius: 10px;
                    background: {'#e0edff' if remetente=='Você' else '#f7f7f7'};
                    ">
                    <b>{remetente}</b> — <small>{data}</small>
                    <br>
                    <div style="margin-top: 6px; font-size: 15px;">
                        {mensagem}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.markdown("---")







# ------------------- TELA DE PLANOS -------------------
# ------------------- TELA DE PLANOS (V2 - MODAL) -------------------
def tela_planos():
    import httpx
    import streamlit as st
    from datetime import date

    st.title("📦 Meus Planos")

    API_URL = (st.session_state.get("API_URL") or "").strip().rstrip("/")
    if not API_URL:
        st.error("API_URL não definido em st.session_state['API_URL'].")
        st.stop()

    # ======================================================
    # 1) DADOS DO USUÁRIO
    # ======================================================
    usuario = st.session_state.get("dados_usuario", {}) or {}
    plano_atual = usuario.get("plano_atual") or "Gratuito"
    if usuario.get("is_admin"):
        plano_atual = "Administrador (acesso total)"

    st.markdown(
        f"""
        <div style='background-color:#f0f8ff; padding: 15px; border-left: 6px solid #007bff; border-radius: 8px; margin-bottom: 10px;'>
            <strong>🔒 Seu plano atual:</strong>
            <span style='font-size:18px; color:#007bff'> {plano_atual} </span><br>
            Para liberar mais recursos do sistema, você pode fazer upgrade agora mesmo.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Botão para atualizar o status após pagamento (webhook)
    col_a, col_b = st.columns([1, 2])
    with col_a:
        if st.button("🔄 Atualizar meu plano agora"):
            token = st.session_state.get("token")
            if not token:
                st.warning("Faça login novamente para atualizar.")
            else:
                try:
                    r = httpx.get(
                        f"{API_URL}/minha-conta",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=30
                    )
                    if r.status_code == 200:
                        st.session_state["dados_usuario"] = r.json() or {}
                        st.success("Plano atualizado com sucesso.")
                        st.rerun()
                    else:
                        st.error((r.json() or {}).get("detail", r.text))
                except Exception as e:
                    st.error(f"Erro ao atualizar: {e}")

    # ======================================================
    # 2) ATIVAÇÃO DE PLANO POR TOKEN (CONSULTORIA)
    # ======================================================
    st.subheader("🔑 Ativar plano com token")
    st.markdown(
        "Se você comprou uma **consultoria MivCast** ou recebeu um código de ativação de um parceiro, "
        "cole seu token abaixo para liberar o acesso por **1 ano** no MivMark."
    )

    token_input = st.text_input("Digite seu token de ativação:", key="token_ativacao_plano")

    if st.button("Ativar token agora"):
        token_texto = (token_input or "").strip()
        if not token_texto:
            st.warning("Digite um token válido.")
        else:
            token_jwt = st.session_state.get("token")
            if not token_jwt:
                st.error("Não foi possível identificar seu login. Saia e entre novamente no sistema antes de ativar o token.")
            else:
                headers = {"Authorization": f"Bearer {token_jwt}", "Content-Type": "application/json"}
                try:
                    resp = httpx.post(
                        f"{API_URL}/usuario/ativar_token",
                        json={"token": token_texto},
                        headers=headers,
                        timeout=30.0,
                    )
                    if resp.status_code == 200:
                        dados = resp.json() or {}
                        novo_plano = dados.get("plano") or "consultoria_full"
                        expira = dados.get("expira_em") or ""
                        st.session_state["dados_usuario"] = st.session_state.get("dados_usuario", {}) or {}
                        st.session_state["dados_usuario"]["plano_atual"] = novo_plano
                        st.success(f"✅ Plano ativado!\n\nPlano: **{novo_plano}**\n\nVálido até: **{expira}**")
                        st.rerun()
                    else:
                        st.error((resp.json() or {}).get("detail", resp.text))
                except Exception as e:
                    st.error(f"Erro ao conectar com o servidor para ativar o token: {e}")

    st.markdown("---")

    # ======================================================
    # 3) LISTAGEM DE PLANOS
    # ======================================================
    try:
        resposta_planos = httpx.get(f"{API_URL}/planos/", timeout=30)
        resposta_planos.raise_for_status()
        planos = resposta_planos.json() or []
    except Exception as e:
        st.error(f"Erro ao buscar planos: {e}")
        return

    # ======================================================
    # 4) CUPONS (escopo=plano)
    # ======================================================
    cupons_plano = []
    try:
        rcu = httpx.get(f"{API_URL}/cupons", params={"escopo": "plano"}, timeout=30)
        if rcu.status_code == 200:
            cupons_plano = rcu.json() or []
    except Exception:
        cupons_plano = []

    def achar_cupom(codigo: str):
        cod = (codigo or "").strip().lower()
        if not cod:
            return None
        for c in cupons_plano:
            if (c.get("codigo") or "").strip().lower() == cod:
                return c
        return None

    # ======================================================
    # 5) ESTADOS DO MODAL
    # ======================================================
    if "plano_modal_aberto" not in st.session_state:
        st.session_state["plano_modal_aberto"] = False
    if "plano_confirm_modal_aberto" not in st.session_state:
        st.session_state["plano_confirm_modal_aberto"] = False
    if "plano_escolhido" not in st.session_state:
        st.session_state["plano_escolhido"] = None
    if "plano_checkout" not in st.session_state:
        st.session_state["plano_checkout"] = {}

    # ======================================================
    # 6) CONFIG: períodos (V1) + descontos por período
    # ======================================================
    PERIODOS = {
        "Mensal": {"periodo_api": "mensal", "meses": 1, "quantidade": 1, "desconto_periodo": 0},
        "3 meses": {"periodo_api": "mensal", "meses": 3, "quantidade": 3, "desconto_periodo": 5},
        "6 meses": {"periodo_api": "mensal", "meses": 6, "quantidade": 6, "desconto_periodo": 10},
        "12 meses": {"periodo_api": "anual", "meses": 12, "quantidade": 1, "desconto_periodo": 0},
    }

    # ======================================================
    # 7) FUNÇÃO: CHAMAR /planos/{id}/comprar com fallback
    # ======================================================
    def comprar_plano_backend(plano_id: int, cupom: str | None, periodo_api: str, quantidade: int):
        token = st.session_state.get("token")
        if not token:
            raise RuntimeError("Token não encontrado. Faça logout/login novamente.")

        headers = {"Authorization": f"Bearer {token}"}

        params = {
            "cupom": (cupom.lower() if cupom else None),
            "periodo": periodo_api,
            "quantidade": int(quantidade),   # ✅ NOVO
            "metodo": "pix",
            "gateway": "mercado_pago",
        }

        url1 = f"{API_URL}/planos/{int(plano_id)}/comprar"
        url2 = f"{API_URL}/api/planos/{int(plano_id)}/comprar"

        try:
            r = httpx.post(url1, headers=headers, params=params, timeout=30)
        except Exception as e:
            raise RuntimeError(f"Erro de rede: {e}")

        if r.status_code == 404:
            r = httpx.post(url2, headers=headers, params=params, timeout=30)

        if r.status_code >= 400:
            try:
                detail = (r.json() or {}).get("detail", r.text)
            except Exception:
                detail = r.text
            raise RuntimeError(str(detail))

        return r.json() or {}


    # ======================================================
    # 8) MODAL 1: escolhas (período, pagamento, cupom)
    # ======================================================
    @st.dialog("Escolha período e condições do plano")
    def modal_escolha_plano():
        plano = st.session_state.get("plano_escolhido") or {}
        plano_id = plano.get("id")
        nome_plano = plano.get("nome") or "Plano"
        preco_mensal = float(plano.get("preco_mensal") or 0.0)

        st.markdown(f"### {nome_plano}")
        st.caption("Selecione o período, aplique cupom (se tiver) e avance para o resumo final.")

        periodo_label = st.radio(
            "🕒 Período",
            list(PERIODOS.keys()),
            index=0,
            horizontal=True
        )

        # (V1) Forma de pagamento — recorrente fica para V2
        tipo_cobranca = st.radio(
            "💳 Tipo de cobrança",
            [
                "Pagamento único (renovação manual)",
                "Recorrente (débito automático) — em breve",
            ],
            index=0
        )
        if "Recorrente" in tipo_cobranca:
            st.info("⏳ A cobrança recorrente estará disponível em breve. Por enquanto, use Pagamento único.")
            st.stop()

        st.caption("A forma de pagamento (PIX, cartão, boleto) é escolhida no checkout do Mercado Pago.")


        cupom_digitado = st.text_input("🎟 Cupom de desconto (opcional)", placeholder="Ex: MIV99").strip()

        # Prévia rápida
        cfg = PERIODOS[periodo_label]
        meses = cfg["meses"]
        desconto_periodo = cfg["desconto_periodo"]
        quantidade = int(cfg.get("quantidade", meses))

        if cfg["periodo_api"] == "anual" and plano.get("preco_anual"):
            base = float(plano.get("preco_anual"))
        else:
            base = preco_mensal * meses
        desconto_p = base * (desconto_periodo / 100.0)
        subtotal = base - desconto_p

        # Economia no anual (comparação visual)
        if cfg["periodo_api"] == "anual":
            valor_lista = preco_mensal * 12
            valor_base = base  # já é o preco_anual ou fallback correto
            economia = max(0.0, valor_lista - valor_base)

            if economia > 0:
                st.info(
                    f"💡 Economia no plano anual: **R$ {economia:.2f}** "
                    f"em relação ao pagamento mensal."
                )


        cupom = achar_cupom(cupom_digitado) if cupom_digitado else None
        cupom_pct = float(cupom.get("desconto_percent") or 0.0) if cupom else 0.0
        desconto_cupom = subtotal * (cupom_pct / 100.0)
        total = max(0.0, subtotal - desconto_cupom)

        st.markdown("---")
        st.markdown("#### Prévia rápida")
        st.write(f"- Valor base: **R$ {base:.2f}**")
        if desconto_periodo:
            st.write(f"- Desconto período ({desconto_periodo}%): **- R$ {desconto_p:.2f}**")
        if cupom_digitado:
            if cupom:
                st.write(f"- Cupom {cupom_digitado.upper()} ({cupom_pct}%): **- R$ {desconto_cupom:.2f}**")
            else:
                st.warning("Cupom não encontrado ou inválido. Você pode prosseguir sem cupom.")

        st.markdown(f"### Total estimado: **R$ {total:.2f}**")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Cancelar"):
                st.session_state["plano_modal_aberto"] = False
                st.session_state["plano_confirm_modal_aberto"] = False
                st.session_state["plano_checkout"] = {}
                st.rerun()

        with col2:
            if st.button("Continuar para confirmar"):
                st.session_state["plano_checkout"] = {
                    "plano_id": int(plano_id),
                    "nome_plano": nome_plano,
                    "preco_mensal": float(preco_mensal),
                    "periodo_label": periodo_label,
                    "periodo_api": cfg["periodo_api"],
                    "quantidade": quantidade,              # ✅ NOVO (ESSENCIAL)
                    "meses": meses,
                    "desconto_periodo": desconto_periodo,
                    "cupom_digitado": cupom_digitado,
                    "cupom_pct": cupom_pct,
                    "total_estimado": float(total),
                    "base": float(base),
                    "desconto_periodo_valor": float(desconto_p),
                    "desconto_cupom_valor": float(desconto_cupom),
                    "tipo_cobranca": tipo_cobranca,
                }
                st.session_state["plano_modal_aberto"] = False
                st.session_state["plano_confirm_modal_aberto"] = True
                st.rerun()

    # ======================================================
    # 9) MODAL 2: resumo final + gerar link MP
    # ======================================================
    @st.dialog("Confirme seu pedido")
    def modal_confirmacao():
        ck = st.session_state.get("plano_checkout") or {}
        if not ck:
            st.error("Nenhum checkout em andamento.")
            if st.button("Fechar"):
                st.session_state["plano_confirm_modal_aberto"] = False
                st.rerun()
            return

        st.markdown("### 📦 Resumo do plano")

        st.write(f"**Plano:** {ck['nome_plano']}")
        st.write(f"**Período:** {ck['periodo_label']} ({ck['meses']} mês(es))")
        st.write(f"**Tipo de cobrança:** {ck['tipo_cobranca']}")
        st.caption("A forma de pagamento (PIX, cartão, boleto) será escolhida no checkout do Mercado Pago.")


        st.markdown("---")
        st.write(f"Valor base: **R$ {ck['base']:.2f}**")

        if ck["desconto_periodo"]:
            st.write(f"Desconto período ({ck['desconto_periodo']}%): **- R$ {ck['desconto_periodo_valor']:.2f}**")

        if ck.get("cupom_digitado"):
            if ck["cupom_pct"] > 0:
                st.write(f"Cupom {ck['cupom_digitado'].upper()} ({ck['cupom_pct']}%): **- R$ {ck['desconto_cupom_valor']:.2f}**")
            else:
                st.write(f"Cupom informado: **{ck['cupom_digitado'].upper()}** (sem desconto aplicado)")

        st.markdown(f"## 💳 Total: **R$ {ck['total_estimado']:.2f}**")

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Voltar"):
                st.session_state["plano_confirm_modal_aberto"] = False
                st.session_state["plano_modal_aberto"] = True
                st.rerun()

        with col2:
            if st.button("Gerar link de pagamento"):
                try:
                    data = comprar_plano_backend(
                        plano_id=int(ck["plano_id"]),
                        cupom=(ck.get("cupom_digitado") or None),
                        periodo_api=str(ck["periodo_api"]),
                        quantidade=int(ck.get("quantidade", 1)),
                    )

                    init_point = data.get("init_point")
                    if init_point:
                        st.success("✅ Link de pagamento gerado com sucesso.")
                        st.link_button("Pagar agora no Mercado Pago", init_point)
                        st.caption("Após pagar, volte aqui e clique em “Atualizar meu plano agora”.")
                    else:
                        st.success("✅ Resposta do backend:")
                        st.json(data)

                except Exception as e:
                    st.error(f"Falha ao gerar pagamento: {e}")

    # ======================================================
    # 10) UI: cards dos planos (simples)
    # ======================================================
    st.subheader("🚀 Planos Disponíveis")
    colunas = st.columns(4)

    for i, plano in enumerate(planos):
        with colunas[i % 4]:
            plano_id = plano.get("id", i)
            nome_plano = plano.get("nome") or "Plano"
            descricao = plano.get("descricao") or ""
            preco_mensal = float(plano.get("preco_mensal") or 0.0)
            modulos = plano.get("modulos_liberados") or []
            destaques = "".join([f"<li>{m}</li>" for m in modulos])

            st.markdown(
                f"""
                <div style='border: 1px solid #ccc; border-radius: 10px; padding: 18px; margin-bottom: 10px;'>
                    <h4 style='margin-bottom:6px;'>{nome_plano}</h4>
                    <p style='margin-top:0; color:#555;'>{descricao}</p>
                    <ul style='margin-top:6px; padding-left:18px;'>{destaques}</ul>
                    <p style='margin-top:10px;'><strong>💰 R$ {preco_mensal:.2f}/mês</strong></p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Plano grátis
            if preco_mensal <= 0:
                st.caption("Plano gratuito não requer pagamento.")
                if nome_plano == plano_atual:
                    st.info("✅ Esse já é seu plano atual.")
                else:
                    st.button(f"Quero esse plano: {nome_plano}", key=f"contratar_free_{plano_id}", disabled=True)
                continue

            # Plano atual
            if nome_plano == plano_atual:
                st.info("✅ Esse já é seu plano atual.")
                continue

            # CTA
            if st.button(f"Quero esse plano: {nome_plano}", key=f"abrir_modal_plano_{plano_id}"):
                st.session_state["plano_escolhido"] = plano
                st.session_state["plano_modal_aberto"] = True
                st.session_state["plano_confirm_modal_aberto"] = False
                st.rerun()

    # ======================================================
    # 11) ABRIR MODAIS (controlados por state)
    # ======================================================
    if st.session_state.get("plano_modal_aberto"):
        modal_escolha_plano()

    if st.session_state.get("plano_confirm_modal_aberto"):
        modal_confirmacao()













def painel_admin():
    import streamlit as st
    import httpx

    st.title("⚙️ Painel Administrativo")

    # ✅ Senha Admin global (vale para Tokens e Usuários)
    st.session_state.setdefault("admin_pwd", "")
    st.session_state["admin_pwd"] = st.text_input(
        "🔐 Senha Admin (ações administrativas)",
        type="password",
        value=st.session_state["admin_pwd"],
        help="Essa senha é usada para Tokens e Usuários no painel admin."
    )

    abas = st.tabs(["🎓 Cursos", "🎟 Tokens", "👥 Usuários", "📱 Aplicativos", "🧩 Planos", "🏷️ Cupons"])

    # -------- CURSOS --------
    with abas[0]:
        painel_admin_cursos()

    # -------- TOKENS --------
    with abas[1]:
        st.subheader("Gerar Token de Ativação")

        senha_admin = st.session_state.get("admin_pwd", "").strip()

        if st.button("Gerar Token"):
            if not senha_admin:
                st.warning("Informe a Senha Admin acima para gerar token.")
            else:
                try:
                    response = httpx.post(
                        f"{API_URL}/admin/gerar_token",
                        params={"senha_admin": senha_admin},
                        timeout=20
                    )
                    if response.status_code == 200:
                        token_gerado = response.json().get("token_ativacao")
                        st.success(f"✅ Token gerado: `{token_gerado}`")
                    elif response.status_code == 401:
                        st.error("Senha admin incorreta.")
                    else:
                        st.error(f"Erro ao gerar token ({response.status_code}): {response.text}")
                except Exception as e:
                    st.error(f"Erro: {e}")

        st.divider()
        st.subheader("🔎 Tokens Gerados")

        if st.button("🔄 Atualizar lista de tokens"):
            if not senha_admin:
                st.warning("Informe a Senha Admin acima para listar tokens.")
            else:
                try:
                    response = httpx.get(
                        f"{API_URL}/admin/listar_tokens",
                        params={"senha_admin": senha_admin},
                        timeout=20
                    )
                    if response.status_code == 200:
                        tokens = response.json()
                        if tokens:
                            for t in tokens:
                                status = "🟢 Ativo" if t.get("ativo") else "❌ Usado"
                                data = t.get("data_criacao") or "N/A"
                                st.markdown(f"`{t.get('token')}` • {status} • Criado em {data}")
                        else:
                            st.info("Nenhum token encontrado.")
                    elif response.status_code == 401:
                        st.error("Senha admin incorreta.")
                    else:
                        st.error(f"Erro ao buscar tokens ({response.status_code}): {response.text}")
                except Exception as e:
                    st.error(f"Erro: {e}")

    # -------- USUÁRIOS --------
    with abas[2]:
        st.subheader("👥 Usuários Cadastrados")

        senha_admin = st.session_state.get("admin_pwd", "").strip()

        if st.button("🔄 Ver usuários cadastrados"):
            if not senha_admin:
                st.warning("Informe a Senha Admin acima para carregar usuários.")
            else:
                try:
                    response = httpx.get(
                        f"{API_URL}/admin/usuarios",
                        params={"senha_admin": senha_admin},
                        timeout=20
                    )

                    if response.status_code == 200:
                        usuarios = response.json()
                        if usuarios:
                            for u in usuarios:
                                nome = u.get("nome", "N/A")
                                email = u.get("email", "N/A")
                                plano = u.get("plano_atual", "nenhum")
                                tipo = u.get("tipo_usuario", "cliente")
                                data = u.get("data_criacao", "N/A")

                                st.markdown(
                                    f"📛 **{nome}**  \n"
                                    f"📧 `{email}`  \n"
                                    f"📦 Plano: `{plano}` • Tipo: `{tipo}` • Criado em: {data}"
                                )
                                st.markdown("---")
                        else:
                            st.info("Nenhum usuário encontrado.")
                    elif response.status_code == 401:
                        st.error("Senha admin incorreta ou não informada.")
                    else:
                        st.error(f"Erro ao buscar usuários ({response.status_code}): {response.text}")

                except Exception as e:
                    st.error(f"Erro: {e}")

    # -------- APLICATIVOS --------
    with abas[3]:
        st.subheader("📱 Gerenciar Aplicativos")
        listar_aplicativos_admin()

    # -------- PLANOS --------
    with abas[4]:
        aba_gerenciar_planos()

    # -------- CUPONS --------
    with abas[5]:
        st.subheader("🏷️ Cupons de Desconto do Sistema")

        token = st.session_state.get("token", "")
        if not token:
            st.error("Token de login não encontrado. Faça login novamente.")
        else:
            subabas = st.tabs(["📦 Cupons de Planos", "🎓 Cupons de Cursos"])

            with subabas[0]:
                painel_admin_cupons(API_URL=API_URL, token=token, escopo="plano")

            with subabas[1]:
                painel_admin_cupons(API_URL=API_URL, token=token, escopo="curso")


def painel_admin_cupons(API_URL: str, token: str, escopo: str):
    import streamlit as st
    import httpx
    from datetime import date

    st.markdown(f"### 🎟 Cupons ({'Planos' if escopo == 'plano' else ('Cursos' if escopo == 'curso' else 'Aplicativos')})")

    headers = {"Authorization": f"Bearer {token}"}

    def _key(*parts):
        # Garante keys únicas e padronizadas
        return "cupom_" + "_".join(str(p) for p in parts)

    # -------------------------------
    # CRIAR CUPOM
    # -------------------------------
    with st.expander("➕ Criar novo cupom", expanded=False):
        with st.form(key=_key("form_create", escopo), clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                codigo = st.text_input("Código do cupom", key=_key("create_codigo", escopo)).strip()
                desconto = st.number_input(
                    "Desconto (%)",
                    min_value=0.0, max_value=100.0,
                    value=10.0, step=1.0,
                    key=_key("create_pct", escopo),
                )
                ativo = st.checkbox("Ativo", value=True, key=_key("create_ativo", escopo))

            with col2:
                descricao = st.text_input("Descrição", key=_key("create_desc", escopo))
                validade_infinita = st.checkbox("Validade infinita", value=True, key=_key("create_inf", escopo))
                valido_ate = None
                if not validade_infinita:
                    valido_ate = st.date_input("Válido até", value=date.today(), key=_key("create_date", escopo))

            alvo_id = st.number_input(
                f"ID do {'Curso' if escopo=='curso' else ('Plano' if escopo=='plano' else 'Aplicativo')} (0 = todos)",
                min_value=0, value=0, step=1,
                key=_key("create_alvo", escopo),
            )

            submitted = st.form_submit_button("Criar cupom")

        if submitted:
            if not codigo:
                st.error("Informe um código.")
            else:
                payload = {
                    "codigo": codigo,
                    "descricao": descricao,
                    "desconto_percent": float(desconto),
                    "escopo": escopo,
                    "valido_ate": None if validade_infinita else str(valido_ate),
                    "ativo": bool(ativo),
                }

                if escopo == "curso":
                    payload["curso_id"] = None if alvo_id == 0 else int(alvo_id)
                elif escopo == "plano":
                    payload["plano_id"] = None if alvo_id == 0 else int(alvo_id)
                elif escopo == "aplicativo":
                    payload["aplicativo_id"] = None if alvo_id == 0 else int(alvo_id)

                try:
                    r = httpx.post(f"{API_URL}/cupons", json=payload, headers=headers, timeout=30)
                    if r.status_code >= 400:
                        try:
                            st.error(r.json().get("detail", "Erro ao criar cupom"))
                        except Exception:
                            st.error(f"Erro ao criar cupom: {r.text}")
                    else:
                        st.success("Cupom criado com sucesso!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")

    st.divider()

    # -------------------------------
    # LISTAR CUPONS
    # -------------------------------
    try:
        r = httpx.get(f"{API_URL}/cupons", params={"escopo": escopo}, headers=headers, timeout=30)
        if r.status_code >= 400:
            try:
                st.error(r.json().get("detail", "Erro ao listar cupons"))
            except Exception:
                st.error(f"Erro ao listar cupons: {r.text}")
            return
        cupons = r.json()
    except Exception as e:
        st.error(f"Erro: {e}")
        return

    if not cupons:
        st.info("Nenhum cupom cadastrado ainda.")
        return

    st.markdown("### 📌 Cupons cadastrados")

    for c in cupons:
        cupom_id = c["id"]
        titulo = f"#{cupom_id} — {c['codigo']} — {c.get('desconto_percent')}% — {'ATIVO' if c.get('ativo') else 'INATIVO'}"

        with st.expander(titulo, expanded=False):
            colA, colB, colC = st.columns([2, 2, 1])

            v = c.get("valido_ate")  # pode vir None ou string ISO
            inf_default = (v is None)

            with st.expander(titulo, expanded=False):

                with st.form(key=f"form_edit_{escopo}_{c['id']}"):
                    colA, colB, colC = st.columns([2, 2, 1])

                    with colA:
                        nova_descricao = st.text_input(
                            "Descrição",
                            value=c.get("descricao") or "",
                            key=f"edit_desc_{escopo}_{c['id']}"
                        )

                        novo_desconto = st.number_input(
                            "Desconto (%)",
                            min_value=0.0,
                            max_value=100.0,
                            value=float(c.get("desconto_percent") or 0.0),
                            step=1.0,
                            key=f"edit_pct_{escopo}_{c['id']}"
                        )

                    with colB:
                        v = c.get("valido_ate")
                        validade_infinita = st.checkbox(
                            "Validade infinita",
                            value=(v is None),
                            key=f"edit_inf_{escopo}_{c['id']}"
                        )

                        novo_valido_ate = None
                        if not validade_infinita:
                            base = date.today() if v is None else date.fromisoformat(v[:10])
                            novo_valido_ate = st.date_input(
                                "Válido até",
                                value=base,
                                key=f"edit_date_{escopo}_{c['id']}"
                            )

                        novo_ativo = st.checkbox(
                            "Ativo",
                            value=bool(c.get("ativo")),
                            key=f"edit_ativo_{escopo}_{c['id']}"
                        )

                    with colC:
                        st.write("")
                        st.write("")
                        salvar = st.form_submit_button("💾 Salvar")

                # 👇 AGORA SIM: ação fora do form
                if salvar:
                    payload = {
                        "descricao": nova_descricao,
                        "desconto_percent": float(novo_desconto),
                        "valido_ate": None if validade_infinita else str(novo_valido_ate),
                        "ativo": bool(novo_ativo),
                    }

                    try:
                        rr = httpx.put(
                            f"{API_URL}/cupons/{c['id']}",
                            json=payload,
                            headers=headers,
                            timeout=30
                        )
                        if rr.status_code >= 400:
                            st.error(rr.json().get("detail", "Erro ao salvar"))
                        else:
                            st.success("Cupom atualizado com sucesso!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")


            if salvar:
                payload = {
                    "descricao": nova_descricao,
                    "desconto_percent": float(novo_desconto),
                    "valido_ate": None if inf else str(novo_valido_ate),
                    "ativo": bool(novo_ativo),
                }
                try:
                    rr = httpx.put(f"{API_URL}/cupons/{cupom_id}", json=payload, headers=headers, timeout=30)
                    if rr.status_code >= 400:
                        try:
                            st.error(rr.json().get("detail", "Erro ao salvar"))
                        except Exception:
                            st.error(f"Erro ao salvar: {rr.text}")
                    else:
                        st.success("Cupom atualizado!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")

            # Excluir com confirmação
            st.markdown("---")
            confirmar = st.checkbox("Confirmar exclusão", key=_key("del_confirm", escopo, cupom_id))
            if st.button("🗑 Excluir", key=_key("btn_del", escopo, cupom_id), disabled=not confirmar):
                try:
                    rr = httpx.delete(f"{API_URL}/cupons/{cupom_id}", headers=headers, timeout=30)
                    if rr.status_code >= 400:
                        try:
                            st.error(rr.json().get("detail", "Erro ao excluir"))
                        except Exception:
                            st.error(f"Erro ao excluir: {rr.text}")
                    else:
                        st.success("Cupom excluído!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")

            # Rodapé
            if escopo == "curso":
                vinculo = f"Curso: {c.get('curso_id')}" if c.get("curso_id") else "Todos os cursos"
            elif escopo == "plano":
                vinculo = f"Plano: {c.get('plano_nome')}" if c.get("plano_nome") and c.get("plano_nome") != "todos" else "Todos os planos"
            else:
                vinculo = f"App: {c.get('aplicativo_id')}" if c.get("aplicativo_id") else "Todos os apps"

            st.caption(f"Validade: {c.get('valido_ate') or '∞'} | {vinculo}")



 




def painel_admin_cursos():
    import streamlit as st
    import httpx

    st.title("📚 Painel de Cursos")

    # =========================
    # Modo Edição de Curso
    # =========================
    if st.session_state.get("modo_edicao") and st.session_state.get("curso_editando"):
        st.subheader("✏️ Editar Curso")

        curso = st.session_state["curso_editando"]

        titulo = st.text_input("Título", value=curso.get("titulo") or "")
        descricao = st.text_area("Descrição", value=curso.get("descricao") or "")
        capa_url = st.text_input("URL da Capa", value=curso.get("capa_url") or "")
        categoria = st.text_input("Categoria", value=curso.get("categoria") or "")
        gratuito = st.checkbox("Gratuito", value=bool(curso.get("gratuito", True)))

        preco_val = float(curso.get("preco") or 0.0)
        preco = st.number_input("Preço", value=preco_val, min_value=0.0, step=0.01, disabled=gratuito)

        destaque = st.checkbox("Destaque", value=bool(curso.get("destaque", False)))
        ordem_curso = st.number_input(
            "Ordem de exibição",
            min_value=1,
            step=1,
            value=int(curso.get("ordem") or 1),
            key="edit_ordem_curso"
        )

        col_a, col_b = st.columns(2)

        with col_a:
            if st.button("💾 Salvar Alterações", use_container_width=True):
                payload = {
                    "titulo": titulo,
                    "descricao": descricao,
                    "capa_url": capa_url,
                    "categoria": categoria,
                    "gratuito": bool(gratuito),
                    "preco": float(preco) if not gratuito else None,
                    "destaque": bool(destaque),
                    "ordem": int(ordem_curso),
                    "ativo": True,
                }
                try:
                    r = httpx.put(f"{API_URL}/cursos/{curso['id']}", json=payload, timeout=30)
                    if r.status_code == 200:
                        st.success("Curso atualizado com sucesso!")
                        st.session_state["modo_edicao"] = False
                        st.session_state["curso_editando"] = None
                        st.rerun()
                    else:
                        st.error(f"Erro ao atualizar curso ({r.status_code}): {r.text}")
                except Exception as e:
                    st.error(f"Erro ao conectar com servidor: {e}")

        with col_b:
            if st.button("❌ Cancelar", use_container_width=True):
                st.session_state["modo_edicao"] = False
                st.session_state["curso_editando"] = None
                st.rerun()

        st.stop()

    # =========================
    # Cadastro de Curso Novo
    # =========================
    st.subheader("➕ Adicionar novo curso")

    titulo_novo = st.text_input("Título do Curso", key="novo_titulo_curso")
    descricao_novo = st.text_area("Descrição", key="novo_desc_curso")
    capa_nova = st.text_input("URL da Imagem de Capa", key="novo_capa_curso")
    categoria_nova = st.text_input("Categoria", key="novo_cat_curso")
    gratuito_novo = st.checkbox("Gratuito", value=True, key="novo_gratuito")
    preco_novo = st.number_input("Preço", min_value=0.0, step=0.01, disabled=gratuito_novo, key="novo_preco")
    destaque_novo = st.checkbox("Destacar no topo", value=False, key="novo_destaque")
    ordem_novo = st.number_input("Ordem de exibição do curso", min_value=1, step=1, value=1, key="novo_ordem")

    if st.button("Salvar mention: Curso", key="btn_salvar_curso"):
        if not titulo_novo.strip():
            st.warning("Informe o título do curso.")
        else:
            payload = {
                "titulo": titulo_novo,
                "descricao": descricao_novo,
                "capa_url": capa_nova,
                "categoria": categoria_nova,
                "gratuito": bool(gratuito_novo),
                "preco": float(preco_novo) if not gratuito_novo else None,
                "destaque": bool(destaque_novo),
                "ordem": int(ordem_novo),
                "ativo": True,
            }
            try:
                r = httpx.post(f"{API_URL}/cursos/admin/curso", json=payload, timeout=30)
                if r.status_code == 200:
                    st.success("Curso cadastrado com sucesso!")
                    st.rerun()
                else:
                    st.error(f"Erro ao salvar curso ({r.status_code}): {r.text}")
            except Exception as e:
                st.error(f"Erro ao salvar curso: {e}")

    st.divider()

    # =========================
    # Carrega lista de cursos (para aula/edição)
    # =========================
    try:
        resp_cursos = httpx.get(f"{API_URL}/cursos/", timeout=30)
        if resp_cursos.status_code != 200:
            st.warning("Não foi possível carregar lista de cursos.")
            cursos = []
        else:
            cursos = resp_cursos.json() or []
    except Exception as e:
        st.error(f"Erro ao buscar cursos: {e}")
        cursos = []

    # =========================
    # Adicionar Aula
    # =========================
    st.subheader("🎞 Adicionar Aula a um Curso")

    if not cursos:
        st.info("Cadastre um curso primeiro para adicionar aulas.")
    else:
        nomes_cursos = {f"{c.get('titulo','Sem título')} (ID {c.get('id')})": c.get("id") for c in cursos}
        curso_escolhido = st.selectbox("Curso", list(nomes_cursos.keys()), key="sel_curso_add_aula")
        id_curso_aula = int(nomes_cursos[curso_escolhido])

        titulo_aula = st.text_input("Título da Aula", key="add_titulo_aula")
        descricao_aula = st.text_area("Descrição da Aula", key="add_desc_aula")
        video = st.text_input("Link do vídeo (YouTube)", key="add_video_aula")
        ordem_aula = st.number_input("Ordem", step=1, value=1, key="add_ordem_aula")

        if st.button("Salvar Aula", key="btn_salvar_aula"):
            if not titulo_aula.strip():
                st.warning("Informe o título da aula.")
            else:
                payload = {
                    "curso_id": id_curso_aula,
                    "titulo": titulo_aula,
                    "descricao": descricao_aula,
                    "video_url": video,
                    "ordem": int(ordem_aula),
                }
                try:
                    r = httpx.post(f"{API_URL}/cursos/admin/aula", json=payload, timeout=30)
                    if r.status_code == 200:
                        st.success("Aula salva com sucesso!")
                        st.rerun()
                    else:
                        st.error(f"Erro ao salvar aula ({r.status_code}): {r.text}")
                except Exception as e:
                    st.error(f"Erro ao salvar aula: {e}")

    st.divider()

    # =========================
    # Editar aulas do curso
    # =========================
    st.subheader("✏️ Editar aulas de um curso")

    if not cursos:
        st.info("Cadastre um curso primeiro.")
    else:
        nomes_cursos_ed = {f"{c.get('titulo','Sem título')} (ID {c.get('id')})": c.get("id") for c in cursos}
        curso_escolhido_ed = st.selectbox(
            "Escolha o curso para gerenciar aulas",
            list(nomes_cursos_ed.keys()),
            key="curso_editar_aulas"
        )
        id_curso_ed = int(nomes_cursos_ed[curso_escolhido_ed])

        try:
            r = httpx.get(f"{API_URL}/cursos/{id_curso_ed}", timeout=30)
            if r.status_code == 200:
                curso_detalhe = r.json()
                aulas = curso_detalhe.get("aulas", []) or []

                if not aulas:
                    st.info("Este curso ainda não tem aulas cadastradas.")
                else:
                    aulas_ordenadas = sorted(aulas, key=lambda a: a.get("ordem") or 0)

                    for aula in aulas_ordenadas:
                        aula_id = aula.get("id")
                        with st.expander(f"{aula.get('ordem') or 0} - {aula.get('titulo','Sem título')} (ID {aula_id})"):
                            novo_titulo = st.text_input(
                                "Título da aula",
                                value=aula.get("titulo") or "",
                                key=f"titulo_aula_{aula_id}",
                            )
                            nova_desc = st.text_area(
                                "Descrição",
                                value=aula.get("descricao") or "",
                                key=f"desc_aula_{aula_id}",
                            )
                            nova_video = st.text_input(
                                "Link do vídeo (YouTube)",
                                value=aula.get("video_url") or "",
                                key=f"video_aula_{aula_id}",
                            )
                            nova_ordem = st.number_input(
                                "Ordem",
                                value=int(aula.get("ordem") or 0),
                                step=1,
                                key=f"ordem_aula_{aula_id}",
                            )

                            if st.button("💾 Salvar alterações desta aula", key=f"salvar_aula_{aula_id}"):
                                payload = {
                                    "titulo": novo_titulo,
                                    "descricao": nova_desc,
                                    "video_url": nova_video,
                                    "ordem": int(nova_ordem),
                                }
                                try:
                                    r_upd = httpx.put(
                                        f"{API_URL}/cursos/admin/aula/{aula_id}",
                                        json=payload,
                                        timeout=30
                                    )
                                    if r_upd.status_code == 200:
                                        st.success("Aula atualizada com sucesso!")
                                        st.rerun()
                                    else:
                                        st.error(f"Erro ao atualizar aula ({r_upd.status_code}): {r_upd.text}")
                                except Exception as e:
                                    st.error(f"Erro ao atualizar aula: {e}")
            else:
                st.error(f"Não foi possível carregar as aulas desse curso ({r.status_code}).")
        except Exception as e:
            st.error(f"Erro ao buscar curso e aulas: {e}")

    st.divider()

    # =========================
    # Cursos Existentes
    # =========================
    st.subheader("📚 Cursos Existentes")

    if not cursos:
        st.warning("Não há cursos para listar.")
    else:
        for curso in cursos:
            with st.expander(f"{curso.get('ordem') or '-'} • {curso.get('titulo','Sem título')} (ID {curso.get('id')})"):
                st.markdown(f"**Categoria:** {curso.get('categoria') or '-'}")
                st.markdown(f"**Gratuito:** {'Sim' if curso.get('gratuito') else 'Não'}")

                if not curso.get("gratuito"):
                    try:
                        st.markdown(f"**Preço:** R$ {float(curso.get('preco') or 0.0):.2f}")
                    except Exception:
                        st.markdown(f"**Preço:** {curso.get('preco')}")

                st.markdown(f"**Destaque:** {'Sim' if curso.get('destaque') else 'Não'}")
                st.markdown(f"**Ativo:** {'Sim' if curso.get('ativo', True) else 'Não'}")

                if st.button(f"✏️ Editar Curso {curso.get('id')}", key=f"editar_{curso.get('id')}"):
                    st.session_state["curso_editando"] = curso
                    st.session_state["modo_edicao"] = True
                    st.rerun()




def get_headers():
    token = st.session_state.get("token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}

def painel_admin_aplicativos():
    st.header("🛠️ Painel de Aplicativos")

    aba = st.radio("Escolha uma opção:", ["📦 Ver Aplicativos", "➕ Novo App", "✏️ Editar App"])

    if aba == "📦 Ver Aplicativos":
        try:
            r = httpx.get(f"{API_URL}/aplicativos", headers=get_headers())
            apps = r.json()
        except Exception as e:
            st.error(f"Erro ao buscar aplicativos: {e}")
            return

        for app in apps:
            with st.container():
                col1, col2 = st.columns([1, 5])
                with col1:
                    st.image(app.get("icone_url", "https://via.placeholder.com/150"), width=80)
                with col2:
                    st.markdown(f"### {app['titulo']}")
                    st.caption(app.get("descricao", ""))
                    st.markdown(f"💼 Categoria: {app.get('categoria', '-')}")
                    preco = "Gratuito" if app['gratuito'] else f"R$ {app['preco']:.2f}"
                    st.markdown(f"💰 Preço: {preco}")
                    st.markdown(f"🟢 Ativo: {'Sim' if app['ativo'] else 'Não'}")
                    editar = st.button("✏️ Editar", key=f"editar_app_{app['id']}")
                    excluir = st.button("🗑 Excluir", key=f"excluir_app_{app['id']}")

                    if editar:
                        st.session_state.app_editando = app
                        st.rerun()

                    if excluir:
                        try:
                            httpx.delete(f"{API_URL}/aplicativos/{app['id']}", headers=get_headers())
                            st.success("App excluído com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao excluir: {e}")

    elif aba == "➕ Novo App":
        with st.form("novo_app"):
            st.subheader("📱 Cadastrar Novo App")
            titulo = st.text_input("Título")
            descricao = st.text_area("Descrição")
            icone_url = st.text_input("URL do Ícone")
            categoria = st.text_input("Categoria")
            gratuito = st.checkbox("Gratuito", value=True)
            preco = st.number_input("Preço (se pago)", min_value=0.0, step=0.01)
            destaque = st.checkbox("Destaque")
            ativo = st.checkbox("Ativo", value=True)
            enviar = st.form_submit_button("💾 Salvar")

            if enviar:
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
                    httpx.post(f"{API_URL}/aplicativos", headers=get_headers(), json=payload)
                    st.success("App cadastrado com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao cadastrar: {e}")

    elif aba == "✏️ Editar App" and "app_editando" in st.session_state:
        app = st.session_state.app_editando
        with st.form("editar_app"):
            st.subheader(f"✏️ Editar App: {app['titulo']}")
            titulo = st.text_input("Título", value=app["titulo"])
            descricao = st.text_area("Descrição", value=app["descricao"])
            icone_url = st.text_input("URL do Ícone", value=app["icone_url"])
            categoria = st.text_input("Categoria", value=app["categoria"])
            gratuito = st.checkbox("Gratuito", value=app["gratuito"])
            preco = st.number_input("Preço (se pago)", min_value=0.0, value=float(app["preco"]))
            destaque = st.checkbox("Destaque", value=app["destaque"])
            ativo = st.checkbox("Ativo", value=app["ativo"])
            salvar = st.form_submit_button("💾 Atualizar")

            if salvar:
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
                    httpx.put(f"{API_URL}/aplicativos/{app['id']}", headers=get_headers(), json=payload)
                    st.success("App atualizado com sucesso!")
                    del st.session_state.app_editando
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao atualizar: {e}")

    elif aba == "✏️ Editar App":
        st.warning("Selecione um aplicativo na aba 'Ver Aplicativos' para editar.")








def tela_cursos():
    if not usuario_tem_acesso("cursos"):
        mostrar_bloqueio_modulo("Cursos")
        st.stop()

    st.header("🎓 Meus Cursos")

    try:
        r = httpx.get(f"{API_URL}/cursos/", headers=get_headers())
        if r.status_code == 200:
            cursos = r.json()
        else:
            st.error("Erro ao carregar cursos.")
            return
    except Exception as e:
        st.error(f"Erro ao buscar cursos: {e}")
        return

    for curso in cursos:
        col1, col2 = st.columns([1, 3])
        with col1:
            st.image(curso["capa_url"], width=120)
        with col2:
            st.subheader(curso["titulo"])
            st.caption(f"Categoria: {curso['categoria']}")
            st.write(curso["descricao"])
            preco = f"R$ {curso['preco']:.2f}" if not curso["gratuito"] else "Gratuito"
            st.markdown(f"💰 **Preço:** {preco}")

            # Se o curso é gratuito ou já está liberado para o usuário
            if curso["gratuito"] or curso["id"] in st.session_state.get("cursos_liberados", []):
                if st.button("▶️ Acessar", key=f"acessar_{curso['id']}"):
                    # Aqui usamos a mesma chave que o main() enxerga
                    st.session_state["curso_liberado"] = curso["id"]
                    st.rerun()
            else:
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("👁️ Espiar", key=f"espiar_{curso['id']}"):
                        st.session_state["curso_espiar"] = curso["id"]
                        st.rerun()
                with col_b2:
                    if st.button("💳 Comprar", key=f"comprar_{curso['id']}"):
                        st.session_state["curso_checkout"] = curso["id"]
                        st.rerun()




def tela_checkout(curso_id):
    import streamlit as st
    import httpx
    from datetime import date

    # ---------------------------------------------------------
    # Helpers (internos)
    # ---------------------------------------------------------
    def _to_date(val):
        # backend pode devolver datetime (string ISO) ou None
        if not val:
            return None
        try:
            return date.fromisoformat(str(val)[:10])
        except:
            return None

    def _reset_cupom():
        st.session_state.pop("checkout_cupom_codigo", None)
        st.session_state.pop("checkout_cupom_percent", None)
        st.session_state.pop("checkout_cupom_desc", None)
        st.session_state.pop("checkout_cupom_curso_id", None)

    # ---------------------------------------------------------
    # 1) Busca curso
    # ---------------------------------------------------------
    try:
        r = httpx.get(f"{API_URL}/cursos/{curso_id}", headers=get_headers(), timeout=30)
        r.raise_for_status()
        curso = r.json()
    except Exception as e:
        st.error(f"Erro ao buscar curso. ({e})")
        return

    st.title("💳 Checkout do Curso")
    st.subheader(curso.get("titulo", "Curso"))
    if curso.get("capa_url"):
        st.image(curso["capa_url"], use_container_width=True)
    if curso.get("descricao"):
        st.write(curso["descricao"])

    preco = float(curso.get("preco") or 0.0)

    # ---------------------------------------------------------
    # 2) Cupom (estado persistente)
    # ---------------------------------------------------------
    if "checkout_cupom_codigo" not in st.session_state:
        _reset_cupom()

    st.markdown("---")
    st.markdown("### 🎟 Aplicar Cupom de Desconto")

    col1, col2 = st.columns([3, 1])

    with col1:
        codigo = st.text_input(
            "Digite o código do cupom",
            value=st.session_state.get("checkout_cupom_codigo") or "",
            key="checkout_input_codigo",
            placeholder="Ex: BEMVINDO10",
        ).strip().lower()

    with col2:
        st.write("")
        validar = st.button("Validar", use_container_width=True)

    # Valida cupom usando /cupons (escopo=curso)
    if validar:
        if not codigo:
            st.warning("Informe um código de cupom.")
        else:
            try:
                headers = get_headers()
                rr = httpx.get(
                    f"{API_URL}/cupons",
                    params={"escopo": "curso"},
                    headers=headers,
                    timeout=30,
                )
                rr.raise_for_status()
                lista = rr.json()

                cupom = next((c for c in lista if (c.get("codigo") or "").strip().lower() == codigo), None)

                if not cupom:
                    _reset_cupom()
                    st.error("❌ Cupom não encontrado.")
                else:
                    # Regras
                    if not bool(cupom.get("ativo", False)):
                        _reset_cupom()
                        st.error("❌ Cupom inativo.")
                    else:
                        valido_ate = _to_date(cupom.get("valido_ate"))
                        if valido_ate and valido_ate < date.today():
                            _reset_cupom()
                            st.error("❌ Cupom expirado.")
                        else:
                            # Se cupom tem curso_id, precisa bater
                            cupom_curso_id = cupom.get("curso_id")
                            if cupom_curso_id is not None and int(cupom_curso_id) != int(curso_id):
                                _reset_cupom()
                                st.error("❌ Este cupom não é válido para este curso.")
                            else:
                                # Aplicar
                                st.session_state["checkout_cupom_codigo"] = cupom.get("codigo")
                                st.session_state["checkout_cupom_percent"] = float(cupom.get("desconto_percent") or 0.0)
                                st.session_state["checkout_cupom_desc"] = cupom.get("descricao") or ""
                                st.session_state["checkout_cupom_curso_id"] = cupom_curso_id

                                st.success(
                                    f"✅ Cupom aplicado: {st.session_state['checkout_cupom_codigo']} "
                                    f"(-{st.session_state['checkout_cupom_percent']:.0f}%)"
                                )

            except Exception as e:
                _reset_cupom()
                st.error(f"Erro ao validar cupom: {e}")

    # Botão remover cupom (se aplicado)
    if st.session_state.get("checkout_cupom_codigo"):
        colx, coly = st.columns([3, 1])
        with colx:
            st.info(
                f"Cupom aplicado: **{st.session_state.get('checkout_cupom_codigo')}** "
                f"({st.session_state.get('checkout_cupom_percent', 0.0):.0f}% OFF) "
                f"{('- ' + st.session_state.get('checkout_cupom_desc')) if st.session_state.get('checkout_cupom_desc') else ''}"
            )
        with coly:
            if st.button("Remover", use_container_width=True):
                _reset_cupom()
                st.rerun()

    # ---------------------------------------------------------
    # 3) Totais (com cupom + PIX)
    # ---------------------------------------------------------
    pct = float(st.session_state.get("checkout_cupom_percent") or 0.0)
    desconto_valor = (pct / 100.0) * preco if pct > 0 else 0.0
    preco_com_cupom = max(0.0, preco - desconto_valor)

    st.markdown("---")
    st.markdown("### 💰 Formas de Pagamento")

    valor_pix = max(0.0, preco_com_cupom * 0.90)  # 10% off no pix

    st.markdown(f"**Preço do curso:** R$ {preco:.2f}")
    if pct > 0:
        st.markdown(f"**Desconto do cupom ({pct:.0f}%):** - R$ {desconto_valor:.2f}")
    st.markdown(f"**Subtotal:** R$ {preco_com_cupom:.2f}")
    st.markdown(f"💸 **PIX (10% OFF):** R$ {valor_pix:.2f}")
    st.markdown("💳 **Cartão:** até 6x sem juros ou até 12x com juros (configurar no gateway)")

    # ---------------------------------------------------------
    # 4) Finalizar Compra (chama backend de compra)
    # ---------------------------------------------------------
    # ... depois que você calculou preco_final e guardou cupom_aplicado/codigo

    if st.button("Finalizar Compra"):
        try:
            payload = {
                "cupom": (codigo.strip().lower() if codigo else None),
                "metodo": "pix",
                "gateway": "mercado_pago",
            }
            rr = httpx.post(
                f"{API_URL}/cursos/{curso_id}/comprar",
                params={"cupom": payload["cupom"], "metodo": payload["metodo"], "gateway": payload["gateway"]},
                headers=get_headers(),
                timeout=30,
            )

            if rr.status_code >= 400:
                try:
                    st.error(rr.json().get("detail", "Erro ao iniciar pagamento"))
                except Exception:
                    st.error(f"Erro ao iniciar pagamento: {rr.text}")
            else:
                data = rr.json()

                # Se cupom 100% liberou na hora
                if "init_point" not in data and "liberado" in (data.get("mensagem","").lower()):
                    st.success(data["mensagem"])
                    st.session_state["curso_checkout"] = None
                    st.rerun()

                # Pagamento real
                init_point = data.get("init_point")
                if init_point:
                    st.success("Link de pagamento gerado. Abra para pagar:")
                    st.link_button("Pagar agora no Mercado Pago", init_point)
                else:
                    st.info(data)

        except Exception as e:
            st.error(f"Erro: {e}")



    # ---------------------------------------------------------
    # 5) Navegação
    # ---------------------------------------------------------
    colA, colB = st.columns(2)

    with colA:
        if st.button("⬅️ Cancelar e voltar", use_container_width=True):
            _reset_cupom()
            st.session_state["curso_checkout"] = None
            st.rerun()

    with colB:
        if st.button("⬅️ Voltar para Cursos", use_container_width=True):
            _reset_cupom()
            st.session_state.pop("curso_checkout", None)
            st.session_state.pop("curso_espiar", None)
            st.rerun()




def tela_detalhe_curso(curso_id: int):
    # Busca dados do curso na API
    try:
        r = httpx.get(f"{API_URL}/cursos/{curso_id}", headers=get_headers())
        if r.status_code != 200:
            st.error("Curso não encontrado.")
            return
        curso = r.json()
    except Exception as e:
        st.error(f"Erro ao buscar curso: {e}")
        return

    # Estamos "espiando" se o estado ativo for curso_espiar
    esta_espiando = (
        st.session_state.get("curso_espiar") == curso_id
        and st.session_state.get("curso_liberado") != curso_id
    )

    st.title(curso.get("titulo", "Curso"))

    if curso.get("capa_url"):
        st.image(curso["capa_url"], use_container_width=True)

    st.markdown(f"**Categoria:** {curso.get('categoria') or 'Sem categoria'}")
    st.markdown(curso.get("descricao", ""))

    aulas = curso.get("aulas") or []

    # ================== MODO ESPIAR / SAIBA MAIS ==================
    if esta_espiando:
        st.markdown("---")
        st.subheader("📚 O que você vai aprender")

        if aulas:
            for aula in sorted(aulas, key=lambda a: a["ordem"]):
                desc = (aula.get("descricao") or "").strip()
                if len(desc) > 120:
                    desc = desc[:120] + "..."
                st.markdown(f"- **{aula['titulo']}** – {desc}")
        else:
            st.info("As aulas deste curso ainda serão adicionadas.")

        st.markdown("---")
        col1, col2 = st.columns([2, 1])

        with col1:
            if st.button("▶️ Acessar curso completo"):
                # troca do modo ESPIAR para ACESSAR (curso_liberado)
                st.session_state["curso_liberado"] = curso_id
                st.session_state.pop("curso_espiar", None)
                st.rerun()

        with col2:
            if st.button("⬅️ Voltar para Cursos"):
                st.session_state.pop("curso_espiar", None)
                st.rerun()

        # Em modo espiar não mostramos os vídeos
        return

    # ================== MODO ACESSO COMPLETO ==================
    st.markdown("---")
    st.subheader("📊 Progresso no Curso")

    aulas_concluidas = []
    try:
        p = httpx.get(f"{API_URL}/cursos/progresso", headers=get_headers())
        aulas_concluidas = p.json().get("aulas_concluidas", [])
    except Exception:
        pass

    total_aulas = len(aulas)
    feitas = len([a for a in aulas if a["id"] in aulas_concluidas])

    if total_aulas > 0:
        st.progress(feitas / total_aulas)
        st.caption(f"{feitas} de {total_aulas} aulas concluídas")
    else:
        st.info("Este curso ainda não possui aulas cadastradas.")

    st.markdown("---")
    st.subheader("🎥 Aulas do Curso")

    aulas_ordenadas = sorted(aulas, key=lambda a: a["ordem"])

    # Grade de 1 coluna
    cols = None
    for idx, aula in enumerate(aulas_ordenadas):
        if idx % 1 == 0:
            cols = st.columns(1)
        col = cols[idx % 1]

        concluida = aula["id"] in aulas_concluidas

        with col:
            st.markdown(f"#### {aula['titulo']} {'✔️' if concluida else ''}")

            # Descrição opcional
            descricao = (aula.get("descricao") or "").strip()
            if descricao:
                st.write(descricao)

            # Vídeo opcional – só mostra se tiver URL válida
            video_url = (aula.get("video_url") or "").strip()
            if video_url:
                st.video(video_url)

            if not concluida:
                if st.button("✅ Marcar como concluída", key=f"concluir_{aula['id']}"):
                    httpx.post(
                        f"{API_URL}/cursos/aula/{aula['id']}/concluir",
                        headers=get_headers(),
                    )
                    st.success("Aula marcada como concluída!")
                    st.rerun()
            else:
                st.success("✔️ Aula já concluída")


    st.markdown("---")
    if st.button("⬅️ Voltar para Cursos"):
        # aqui está o ponto que estava te “prendendo”
        st.session_state.pop("curso_checkout", None)
        st.session_state.pop("curso_espiar", None)
        st.session_state.pop("curso_liberado", None)
        st.rerun()










def tela_aplicativos():
    if not usuario_tem_acesso("aplicativos"):
        mostrar_bloqueio_modulo("Aplicativos")
        st.stop()

    st.title("📱 Aplicativos Disponíveis")

    try:
        r = httpx.get(f"{API_URL}/aplicativos", headers=get_headers())
        apps = r.json()
    except Exception as e:
        st.error(f"Erro ao buscar aplicativos: {e}")
        return

    colunas = st.columns(4)
    for idx, app in enumerate(apps):
        col = colunas[idx % 4]
        with col:
            st.image(app["icone_url"], use_container_width=True)
            st.markdown(f"### {app['titulo']}")
            st.caption(app["descricao"][:80] + "...")
            preco = app.get("preco")
            if app["gratuito"]:
                st.markdown("🟢 Gratuito")
            else:
                st.markdown(f"💰 R$ {preco:.2f}")

            if app["gratuito"] or app["id"] in st.session_state.get("apps_liberados", []):
                if st.button("▶️ Acessar", key=f"acessar_{app['id']}"):
                    st.session_state["app_liberado"] = app["id"]
                    st.rerun()
            else:
                if st.button("💳 Comprar", key=f"comprar_{app['id']}"):
                    st.session_state["app_checkout"] = app["id"]
                    st.rerun()

def tela_meus_aplicativos():
    st.title("📲   Meus Apps")

    try:
        r = httpx.get(f"{API_URL}/aplicativos", headers=get_headers())
        apps = r.json()
    except:
        st.warning("Erro ao carregar aplicativos")
        return

    liberados = st.session_state.get("apps_liberados", [])
    comprados = st.session_state.get("comprados", [])

    for app in apps:
        if app["gratuito"] or app["id"] in liberados or app["id"] in comprados:
            col1, col2 = st.columns([1, 3])
            with col1:
                # ✅ Verificação segura do ícone
                icone = app.get("icone_url")
                if not icone:
                    icone = "https://via.placeholder.com/150"
                st.image(icone, width=100)

            with col2:
                st.subheader(app.get("titulo", "Sem Título"))
                st.caption(app.get("descricao", ""))
                if st.button("🚀 Abrir App", key=f"usar_{app['id']}"):
                    st.info("Este app será aberto futuramente...")

def tela_detalhe_app(app_id):
    st.title("📲 Detalhes do Aplicativo")
    st.info(f"Função futura. ID do app: {app_id}")

def tela_checkout_app(app_id):
    st.title("💳 Finalizar Compra do App")
    st.info(f"Função futura. Checkout do app ID: {app_id}")



def tela_contato_mivcast():
    import streamlit as st
    import os
    import urllib.parse
    from datetime import datetime

    # Import do utilitário de e-mail (backend)
    # Ajuste o caminho se seu projeto tiver outra estrutura
    try:
        from backend.utils.email_utils import enviar_email, EMAIL_ADMIN
        EMAIL_UTILS_OK = True
    except Exception as e:
        EMAIL_UTILS_OK = False
        EMAIL_UTILS_ERRO = str(e)

    st.title("📞 Contato e Suporte — MivCast")

    # =========================
    # CONFIG
    # =========================
    SUPORTE_EMAIL = (os.getenv("MIVCAST_SUPORTE_EMAIL", "sitesmiv@gmail.com") or "").strip()

    # Seu WhatsApp fixo (formato wa.me)
    WHATSAPP_NUMERO = "5517997061273"

    SITE_URL = (os.getenv("www.mivcast.com.br", "") or "").strip()

    # =========================
    # Cards de contato
    # =========================
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("E-mail")
        st.write(f"📧 **{SUPORTE_EMAIL}**")
        st.caption("Atendimento, suporte, sugestões e solicitações comerciais.")

    with col2:
        st.subheader("WhatsApp")
        st.write(f"📱 **+55 (17) 99706-1273**")
        st.caption("Mais rápido para suporte e alinhamentos.")

    with col3:
        st.subheader("Site / Apresentação")
        if SITE_URL:
            st.write(f"🌐 {www.mivcast.com.br}")
        else:
            st.info("www.mivcast.com.br")

    st.divider()

    # =========================
    # Sobre a MivCast
    # =========================
    with st.expander("Conhecer a MivCast e o que fazemos", expanded=False):
        st.markdown(
            """
**A MivCast** é uma agência e plataforma que organiza e executa estratégias de marketing com foco em resultado prático.
Aqui no MivMark, você tem módulos que ajudam a estruturar sua presença digital, rotinas e ações de crescimento.

**Podemos te apoiar com:**
- Branding (identidade, posicionamento, tom de voz)
- Tráfego pago (Google Ads / Meta Ads)
- Conteúdo e social media (planejamento e criativos)
- Sites e páginas (institucional, landing page, chat com IA)
- Estruturação comercial (ofertas, funil, processo de atendimento)
- Consultoria empresarial e planos de execução
            """.strip()
        )

    st.divider()

    # =========================
    # Formulário de suporte
    # =========================
    st.subheader("Abrir um chamado (suporte, sugestão ou interesse comercial)")

    usuario = st.session_state.get("dados_usuario", {}) or {}
    nome_user = (usuario.get("nome") or "").strip()
    email_user = (usuario.get("email") or "").strip()
    plano_user = (usuario.get("plano_atual") or "Gratuito").strip()

    with st.form("form_suporte_mivcast"):
        c1, c2 = st.columns(2)
        with c1:
            nome = st.text_input("Seu nome", value=nome_user, placeholder="Ex.: Matheus Nascimento")
        with c2:
            email = st.text_input("Seu e-mail", value=email_user, placeholder="Ex.: seuemail@gmail.com")

        tipo = st.selectbox(
            "Tipo de contato",
            [
                "Suporte (bug/erro)",
                "Sugestão de melhoria",
                "Dúvida sobre planos/assinatura",
                "Interesse em serviço (orçamento)",
                "Outro",
            ],
        )

        prioridade = st.select_slider("Prioridade", options=["Baixa", "Média", "Alta"], value="Média")

        assunto = st.text_input("Assunto", placeholder="Ex.: Erro ao abrir o módulo de Cursos")
        mensagem = st.text_area(
            "Explique com detalhes",
            placeholder="Se for erro, descreva o que você clicou, o que esperava e o que aconteceu. Se possível, cole o texto do erro.",
            height=160,
        )

        anexos = st.text_input(
            "Links úteis (opcional)",
            placeholder="Cole aqui links/imagens (Print no Drive, Imgur, etc.)",
        )

        enviado = st.form_submit_button("Gerar mensagem e opções de envio")

    if enviado:
        if not nome or not email or not assunto or not mensagem:
            st.error("Preencha pelo menos: Nome, E-mail, Assunto e Mensagem.")
            return

        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
        contexto_txt = (
            f"CHAMADO MIVCAST\n"
            f"Data/Hora: {agora}\n"
            f"Nome: {nome}\n"
            f"E-mail: {email}\n"
            f"Plano: {plano_user}\n"
            f"Tipo: {tipo}\n"
            f"Prioridade: {prioridade}\n"
            f"Assunto: {assunto}\n\n"
            f"Mensagem:\n{mensagem}\n\n"
            f"Links/Anexos:\n{anexos or '-'}\n"
        )

        st.success("Mensagem pronta. Agora escolha o canal para enviar.")
        st.code(contexto_txt, language="text")

        # =========================
        # 1) WhatsApp (abrir)
        # =========================
        texto_wa = urllib.parse.quote(contexto_txt)
        wa_url = f"https://wa.me/{WHATSAPP_NUMERO}?text={texto_wa}"
        st.link_button("Abrir WhatsApp com a mensagem pronta", wa_url)

        # =========================
        # 2) E-mail automático (SMTP)
        # =========================
        st.subheader("Enviar por e-mail")

        if EMAIL_UTILS_OK:
            destino = (EMAIL_ADMIN or SUPORTE_EMAIL).strip()
            st.caption(f"Destino do chamado: {destino}")

            assunto_email = f"[MivMark] {tipo} — {assunto}"

            corpo_html = f"""
            <h3>Chamado MivCast</h3>
            <pre style="font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;">
{contexto_txt}
            </pre>
            """

            colA, colB = st.columns(2)

            with colA:
                if st.button("Enviar e-mail agora (automático)", key="btn_enviar_email_agora"):
                    with st.spinner("Enviando e-mail para o suporte e confirmação para você..."):

                        # 1) Envia para o admin/suporte
                        ok_admin = enviar_email(
                            destinatario=destino,
                            assunto=assunto_email,
                            corpo_html=corpo_html,
                            corpo_texto=contexto_txt,
                            cc_admin=False
                        )

                        # 2) Confirmação para o usuário (se e-mail válido foi preenchido)
                        ok_user = True
                        user_email = (email or "").strip()

                        if user_email:
                            assunto_conf = "Recebemos seu chamado — MivCast"
                            corpo_txt_conf = (
                                f"Olá, {nome}.\n\n"
                                "Recebemos seu chamado e vamos responder em breve.\n"
                                "Abaixo está uma cópia do que foi enviado:\n\n"
                                f"{contexto_txt}\n"
                                "Atenciosamente,\n"
                                "Equipe MivCast\n"
                            )

                            corpo_html_conf = f"""
                            <p>Olá, <b>{nome}</b>.</p>
                            <p>Recebemos seu chamado e vamos responder em breve.</p>
                            <p>Abaixo está uma cópia do que foi enviado:</p>
                            <pre style="font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;">
                {contexto_txt}
                            </pre>
                            <p>Atenciosamente,<br/>Equipe MivCast</p>
                            """

                            ok_user = enviar_email(
                                destinatario=user_email,
                                assunto=assunto_conf,
                                corpo_html=corpo_html_conf,
                                corpo_texto=corpo_txt_conf,
                                cc_admin=False
                            )

                    if ok_admin and ok_user:
                        st.success("Chamado enviado para o suporte e confirmação enviada para seu e-mail.")
                    elif ok_admin and not ok_user:
                        st.warning("Chamado enviado para o suporte, mas não foi possível enviar a confirmação para o seu e-mail.")
                    else:
                        st.error("Falha ao enviar o e-mail para o suporte. Verifique as variáveis EMAIL_USER/EMAIL_PASSWORD no ambiente.")


            with colB:
                # Alternativa: mailto (abre cliente de e-mail do usuário)
                subject = urllib.parse.quote(assunto_email)
                body = urllib.parse.quote(contexto_txt)
                mailto = f"mailto:{destino}?subject={subject}&body={body}"
                st.link_button("Abrir e-mail (mailto) com a mensagem pronta", mailto)

        else:
            st.warning(
                "Não foi possível importar o email_utils do backend. "
                "O envio automático por SMTP ficará indisponível neste ambiente."
            )
            st.caption(f"Detalhe técnico: {EMAIL_UTILS_ERRO}")
            # Ainda oferece mailto
            subject = urllib.parse.quote(f"[MivMark] {tipo} — {assunto}")
            body = urllib.parse.quote(contexto_txt)
            mailto = f"mailto:{SUPORTE_EMAIL}?subject={subject}&body={body}"
            st.link_button("Abrir e-mail (mailto) com a mensagem pronta", mailto)

    st.divider()

    # =========================
    # Atalhos rápidos
    # =========================
    st.subheader("Atalhos rápidos")
    cols = st.columns(3)

    with cols[0]:
        st.write("• Suporte por e-mail")
        st.caption(SUPORTE_EMAIL)

    with cols[1]:
        st.write("• Suporte por WhatsApp")
        st.caption("+55 (17) 99706-1273")

    with cols[2]:
        if SITE_URL:
            st.write("• Conhecer a MivCast")
            st.caption(SITE_URL)
        else:
            st.write("• Apresentação")
            st.caption("www.mivcast.com.br")

    st.info(
        "Se você quiser, o próximo passo é transformar isso em um sistema de tickets: "
        "salvar no banco, gerar protocolo, e permitir histórico do usuário dentro do MivMark."
    )



# ------------------- INTERFACE PRINCIPAL -------------------

def main():

    query_params = st.query_params
    modo_cadastro = "cadastro" in query_params
    logado = st.session_state.token is not None

    # Se o usuário não estiver logado e clicou para se cadastrar
    if not logado and modo_cadastro:
        tela_cadastro()
        return

    # Se não estiver logado e não é cadastro → mostrar tela de login
    if not logado:
        tela_login_personalizada()
        return

    # Agora segue normalmente com usuário logado
    if st.session_state.token:

        # 🔤 "Menu de módulos" em uma caixinha preta ao lado do >>
        st.markdown("""
        <style>
        @media (max-width: 768px) {

            /* Header fixo no topo */
            [data-testid="stHeader"] {
                position: sticky;
                top: 0;
                z-index: 999;
            }

            /* Caixinha preta ao lado do >> */
            [data-testid="stHeader"]::after {
                content: "👈🏻 Menu de módulos";
                position: absolute;
                left: 55px;
                top: 16px;              /* altura ajustada pra ficar na linha do >> */
                padding: 6px 12px;
                background-color: #000000;
                color: #ffffff;
                border-radius: 999px;
                font-size: 12px;
                font-weight: 600;
                white-space: nowrap;
            }
        }
        </style>
        """, unsafe_allow_html=True)

        # 🔁 Script para FECHAR automaticamente o menu lateral no mobile (versão 2)
        st.markdown(
            """
            <script>
            (function() {
              function isMobile() {
                return window.innerWidth <= 768;
              }

              function encontrarBotaoToggle() {
                const candidatos = Array.from(document.querySelectorAll("button"));
                return candidatos.find(btn => {
                  const aria = (btn.getAttribute("aria-label") || "").toLowerCase();
                  const title = (btn.getAttribute("title") || "").toLowerCase();
                  const texto = (btn.innerText || "").toLowerCase();

                  return (
                    aria.includes("sidebar") ||
                    aria.includes("barra lateral") ||
                    title.includes("sidebar") ||
                    title.includes("barra lateral") ||
                    texto.includes("≪") || texto.includes("≫")
                  );
                }) || null;
              }

              function fecharSidebar() {
                const toggle = encontrarBotaoToggle();
                if (toggle) toggle.click();
              }

              document.addEventListener("click", function(event) {
                if (!isMobile()) return;

                const labelRadio = event.target.closest('label[data-baseweb="radio"]') || event.target.closest("label");
                if (!labelRadio) return;

                setTimeout(function() {
                  fecharSidebar();
                }, 400);
              }, true);

              let touchStartX = null;

              document.addEventListener("touchstart", function(e) {
                if (!isMobile()) return;
                const touch = e.touches[0];
                touchStartX = touch.clientX;
              }, { passive: true });

              document.addEventListener("touchend", function(e) {
                if (!isMobile()) return;
                if (touchStartX === null) return;

                const touch = e.changedTouches[0];
                const deltaX = touch.clientX - touchStartX;

                if (deltaX < -60) {
                  fecharSidebar();
                }

                touchStartX = null;
              });
            })();
            </script>
            """,
            unsafe_allow_html=True,
        )

        obter_dados_usuario()
        usuario = st.session_state.dados_usuario
        plano = usuario.get("plano_atual") or "Gratuito"

        logo_url = usuario.get("logo_url")
        if logo_url:
            st.sidebar.image(logo_url, use_container_width=True)
        else:
            st.sidebar.markdown("📌 Sua logo aparecerá aqui")

        # Admin: acesso total
        if usuario.get("is_admin") or usuario.get("tipo_usuario") == "admin":
            plano = "Administrador (acesso total)"

        st.sidebar.markdown(f"🔐 **Plano:** `{plano}`")

        if plano == "pendente":
            st.error("❌ Sua conta ainda não está ativada.")
            st.warning("Use seu token de ativação para concluir o cadastro.")
            if st.button("Sair"):
                st.session_state.token = None
                st.session_state.dados_usuario = {}
                st.rerun()
            return

        if usuario.get("tipo_usuario") == "admin":
            st.sidebar.markdown("---")
            if st.sidebar.button("⚙️ Painel Admin"):
                st.session_state.admin = True

    # --- Painel admin mantém a lógica atual ---
    if st.session_state.admin:
        painel_admin()
        if st.button("⬅️ Voltar para o sistema"):
            st.session_state.admin = False
            st.rerun()
        return


    # =========================================================
    # ✅ CONTROLE GLOBAL DE ACESSO POR MÓDULO (PLANOS)
    # =========================================================

    # Slug do módulo -> Nome bonito (para mostrar no aviso)
    MODULOS_CATALOGO = {
        "empresa": "🏢 Empresa",
        "saude": "❤️ Saúde da Empresa",
        "consultoria": "📋 Consultoria",
        "cursos": "🎓 Cursos",
        "aplicativos": "📱 Aplicativos",
        "orcamento": "💰 Orçamento",
        "agenda": "📅 Agenda",
        "consultor_mensal": "📣 Consultor Mensal",
        "arquivo": "📁 Arquivos",
        "mark": "🤖 MARK IA",
        "site_chat": "🌐 Site e Chat",
                   "contato_mivcast": "📞 Contato MivCast",
    }

    # Item do menu -> slug do módulo (ou None se não bloqueia)
    MENU_PARA_MODULO = {
        "🏠 **Início**": None,
        "💳 Planos": None,
        "🏢 **Empresa**": "empresa",
        "❤️ **Saúde da Empresa**": "saude",
        "📋 **Consultoria**": "consultoria",
        "🎓 **Cursos**": "cursos",
        "📘 **Meus Cursos**": "cursos",
        "📱 **Aplicativos**": "aplicativos",
        "📲   **Meus Apps**": "aplicativos",
        "💰 **Orçamento**": "orcamento",
        "📅 **Agenda**": "agenda",
        "📣 **Consultor Mensal**": "consultor_mensal",
        "📁 **Arquivos**": "arquivo",
        "🤖 **MARK IA**": "mark",
        "🌐 **Site e Chat**": "site_chat",
                   "📞 **Contato MivCast**": None,
        "🚪 **Sair**": None,
    }

    def exigir_acesso(modulo_slug: str):
        """Bloqueia a tela se o usuário não tiver acesso ao módulo."""
        if not modulo_slug:
            return

        from verificar_acesso import usuario_tem_acesso, planos_que_liberam

        if not usuario_tem_acesso(modulo_slug):
            nome_bonito = MODULOS_CATALOGO.get(modulo_slug, modulo_slug)
            planos = planos_que_liberam(modulo_slug)
            planos_txt = ", ".join(planos) if planos else "planos superiores"

            st.warning(
                f"🔒 Este módulo ({nome_bonito}) está disponível apenas nos planos: **{planos_txt}**."
            )
            st.stop()


    # --- MENU LATERAL: sempre aparece ---
    st.sidebar.title("📚 Menu")
    escolha = st.sidebar.radio(
        "Navegar para:",
        [
            "🏠 **Início**",
            "💳 Planos",
            "🏢 **Empresa**",
            "❤️ **Saúde da Empresa**",
            "📋 **Consultoria**",
            "🎓 **Cursos**",
            "📘 **Meus Cursos**",
            "📱 **Aplicativos**",
            "📲   **Meus Apps**",
            "💰 **Orçamento**",
            "📅 **Agenda**",
            "📣 **Consultor Mensal**",
            "📁 **Arquivos**",
            "🤖 **MARK IA**",
            "🌐 **Site e Chat**",
            "📞 **Contato MivCast**",
            "🚪 **Sair**"
        ],
        key="menu_principal",
    )

    # ✅ Bloqueio global (antes de carregar qualquer tela)
    exigir_acesso(MENU_PARA_MODULO.get(escolha))


    # --- ESTADOS DE CURSO: sobrescrevem o conteúdo da tela,
    # mas o menu continua visível na esquerda ---
    if st.session_state.get("curso_checkout"):
        tela_checkout(st.session_state["curso_checkout"])
        return

    if st.session_state.get("curso_liberado"):
        tela_detalhe_curso(st.session_state["curso_liberado"])
        return

    if st.session_state.get("curso_espiar"):
        tela_detalhe_curso(st.session_state["curso_espiar"])
        return


    if escolha == "🏠 **Início**":
        tela_inicio()

    elif escolha == "💳 Planos":
        tela_planos()

    elif escolha == "🏢 **Empresa**":
        tela_empresa()

    elif escolha == "❤️ **Saúde da Empresa**":
        from saude_empresa import tela_saude_empresa
        tela_saude_empresa()

    elif escolha == "📋 **Consultoria**":
        tela_consultoria()

    elif escolha == "🎓 **Cursos**":
        from cursos import tela_cursos
        tela_cursos()

    elif escolha == "📘 **Meus Cursos**":
        from cursos import tela_meus_cursos
        tela_meus_cursos()

    elif escolha == "📱 **Aplicativos**":
        from aplicativos import tela_aplicativos
        tela_aplicativos()

    elif escolha == "📲   **Meus Apps**":
        from aplicativos import tela_meus_aplicativos
        tela_meus_aplicativos()

    elif escolha == "💰 **Orçamento**":
        from orcamento import tela_orcamento
        try:
            r = httpx.get(f"{API_URL}/empresa", headers=get_headers())
            dados_empresa = r.json() if r.status_code == 200 else {}
        except Exception as e:
            dados_empresa = {}
            st.error(f"Erro ao buscar dados da empresa: {e}")
        tela_orcamento(dados_empresa)

    elif escolha == "📅 **Agenda**":
        tela_agenda()

    elif escolha == "📣 **Consultor Mensal**":
        tela_consultor_mensal()

    elif escolha == "📁 **Arquivos**":
        tela_arquivos()

    elif escolha == "🤖 **MARK IA**":
        tela_mark_ia()

    elif escolha == "🌐 **Site e Chat**":
        tela_site_cliente()

    elif escolha == "📞 **Contato MivCast**":
        tela_contato_mivcast()

    elif escolha == "🚪 **Sair**":
        st.session_state.token = None
        st.session_state.modo_demo = False
        st.session_state.setores_visitados = []
        st.session_state.dados_usuario = {}
        st.session_state.admin = False
        st.success("Logout realizado.")
        st.rerun()



# Executa o app
if __name__ == "__main__":
    main()
