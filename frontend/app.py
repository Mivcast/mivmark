import streamlit as st
from agenda import tela_agenda  # ✅ Importa a versão visual com calendário
from datetime import datetime, timedelta

# ⚙️ A configuração da página deve ser a PRIMEIRA chamada do Streamlit
st.set_page_config(layout="wide")

import httpx
import datetime
import streamlit.components.v1 as components
from site_cliente import tela_site_cliente
from aplicativos import listar_aplicativos_admin
from admin.planos import aba_gerenciar_planos


API_URL = "https://mivmark-backend.onrender.com"


def usuario_tem_acesso(modulo: str) -> bool:
    usuario = st.session_state.get("dados_usuario", {})
    plano = usuario.get("plano_atual")

    if not plano:
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

# ------------------- ESTADO GLOBAL -------------------

if "token" not in st.session_state:
    st.session_state.token = None
if "modo_demo" not in st.session_state:
    st.session_state.modo_demo = False
if "setores_visitados" not in st.session_state:
    st.session_state.setores_visitados = []
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
        dados = r.json()
        total = dados.get("aulas_total", 1)
        concluidas = dados.get("aulas_concluidas", 0)
        pct_curso = int((concluidas / total) * 100) if total > 0 else 0
    except:
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
    import base64
    from pathlib import Path

    st.set_page_config(layout="wide")

    # Caminho da imagem de fundo
    caminho_imagem = Path("frontend/img/telalogin.jpg")  # ou .png se for o caso
    imagem_base64 = ""
    if caminho_imagem.exists():
        with open(caminho_imagem, "rb") as f:
            imagem_base64 = base64.b64encode(f.read()).decode("utf-8")

    # CSS com imagem de fundo usando base64 e layout 60/40
    st.markdown(f"""
        <style>
        * {{ font-family: 'Segoe UI', sans-serif; }}
        html, body {{
            margin: 0 !important;
            padding: 0 !important;
        }}
        .css-18e3th9, .block-container {{
            padding: 0rem !important;
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
            margin: auto;
            padding: 60px 40px;
            background-color: white;
        }}
        h1 {{
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .subtitle {{
            color: #666;
            margin-bottom: 40px;
        }}

        /* 🔵 INPUTS E CAMPOS */
        .stTextInput, .stPassword {{
            width: 90% !important;
            margin-bottom: 10px;
        }}
        .stTextInput > div > input,
        .stPassword > div > input {{
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #ccc;
            width: 100%;
        }}

        /* 🔵 BOTÃO */
        .stButton button {{
            background-color: #265df2;
            color: white;
            font-weight: bold;
            padding: 12px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            width: 90%;
        }}

        .stButton button:hover {{
            background-color: #1d47c8;
        }}

        .link, .bottom-text {{
            font-size: 14px;
            color: #265df2;
            margin-top: 10px;
        }}
        @media(max-width: 768px) {{
            .left {{
                display: none;
            }}
            .right {{
                width: 90% !important;
                padding: 20px 24px !important;
                max-width: 100% !important;
                margin: 0 auto !important;
            }}
            .stTextInput > div > input,
            .stPassword > div > input,
            .stButton button {{
                width: 90% !important;
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

        st.image("img/mivlogopreta.png", width=120)
        st.markdown("<h1>Login</h1>", unsafe_allow_html=True)
        st.markdown("<p class='subtitle'>Acesse sua conta para gerenciar seu sistema.</p>", unsafe_allow_html=True)

        st.markdown("**E-mail**")
        email = st.text_input("E-mail", placeholder="Digite seu e-mail ou usuário", label_visibility="collapsed")

        st.markdown("**Senha**")
        senha = st.text_input("", placeholder="Digite sua senha", type="password")

        st.markdown("<div class='link'>Esqueci minha senha</div>", unsafe_allow_html=True)

        if st.button("Acessar meu Sistema", use_container_width=True):
            token = login_usuario(email, senha)
            if token:
                st.session_state.token = token
                obter_dados_usuario()
                st.success("✅ Login realizado com sucesso!")
                st.rerun()

        # Botão cinza como DIV estilizado com clique
        st.markdown("""
            <div style="margin-top: 15px;">
                <button style="width: 90%; padding: 12px 20px; background-color: #d6d6d6; color: black; border: none; border-radius: 8px; font-size: 15px; cursor: pointer;"
                    onclick="window.location.href='?demo=true'">
                    Quer apenas conhecer o sistema? Faça um login rápido
                </button>
            </div>
        """, unsafe_allow_html=True)

        # Link para cadastro

        st.markdown("Ainda não tem cadastro na MivCast?")

        if st.button("📩 Cadastre-se agora"):
            st.query_params = {"cadastro": "true"}
            st.rerun()







def login_usuario(email, senha):
    """Realiza login e retorna o token"""
    import httpx
    import streamlit as st

    API_URL = "https://mivmark-backend.onrender.com"

    # payload deve estar em formato de formulário (não JSON)
    data = {
        "username": email,
        "password": senha,
        "grant_type": "password"  # <-- isso é OBRIGATÓRIO para OAuth2PasswordRequestForm
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        r = httpx.post(f"{API_URL}/login", data=data, headers=headers)
        if r.status_code == 200:
            resposta = r.json()
            st.success("✅ Login realizado com sucesso!")
            st.session_state.token = resposta["access_token"]
            st.session_state.usuario = resposta
            st.rerun()
        else:
            st.error(f"Erro no login: {r.text}")
    except Exception as e:
        st.error(f"Erro ao conectar: {e}")





# ------------------- CADASTRO E LOGIN -------------------

def tela_cadastro():
    import streamlit as st
    import httpx

    API_URL = "https://mivmark-backend.onrender.com"
    st.title("📝 Criar sua conta")

    cupons_validos = {
        "BEMVINDO10": ("porcentagem", 10),
        "MIV99": ("porcentagem", 90),
        "PROMO25": ("porcentagem", 25),
        "VIP50": ("fixo", 50),
        "R10OFF": ("fixo", 10)
    }

    planos_info = {
        "Gratuito": 0.0,
        "Essencial": 47.90,
        "Profissional": 97.90,
        "Premium": 195.90
    }

    if "plano_escolhido" not in st.session_state:
        st.session_state.plano_escolhido = "Gratuito"
    plano_selecionado = st.session_state.plano_escolhido

    st.subheader("📦 Escolha um plano")
    col1, col2 = st.columns(2)

    def card_plano(nome, emoji, cor, preco, tooltip):
        selecionado = plano_selecionado == nome
        borda = "3px solid #00c851" if selecionado else "1px solid #ccc"
        st.markdown(f"""
            <div style='background-color:{cor}; padding: 15px; border-radius: 12px; border:{borda}; margin-bottom:10px;'>
                <h4 style='margin-bottom:5px'>{emoji} Plano {nome}</h4>
                <ul>{tooltip}</ul>
                <strong>💰 R$ {preco:.2f}</strong>
            </div>
        """, unsafe_allow_html=True)
        if st.button(f"Selecionar {nome}", key=f"btn_{nome}"):
            st.session_state.plano_escolhido = nome
            st.rerun()

    with col1:
        card_plano("Gratuito", "🆓", "#eafaf1", planos_info["Gratuito"], "<li>Empresa</li><li>Saúde</li>")
        card_plano("Profissional", "🚀", "#fff9e6", planos_info["Profissional"], "<li>Avançado</li><li>Todos do Essencial</li>")

    with col2:
        card_plano("Essencial", "💼", "#f0f4ff", planos_info["Essencial"], "<li>Orçamento</li><li>Aplicativos</li>")
        card_plano("Premium", "👑", "#fbeef7", planos_info["Premium"], "<li>Suporte Premium</li><li>Tudo incluso</li>")

    st.markdown("---")
    st.subheader("📋 Dados de Cadastro")

    with st.form("form_cadastro"):
        nome = st.text_input("👤 Nome completo")
        email = st.text_input("📧 E-mail")
        senha = st.text_input("🔒 Senha", type="password")

        preco = planos_info[plano_selecionado]
        preco_final = preco
        desconto = 0

        cupom_input = ""
        if plano_selecionado != "Gratuito":
            cupom_input = st.text_input("💳 Cupom de desconto").upper()
            if cupom_input in cupons_validos:
                tipo, valor = cupons_validos[cupom_input]
                if tipo == "porcentagem":
                    desconto = preco * (valor / 100)
                elif tipo == "fixo":
                    desconto = valor
                preco_final = max(0, round(preco - desconto, 2))
                st.success(f"🎉 Cupom aplicado! Novo valor: R$ {preco_final:.2f}")
            elif cupom_input:
                st.warning("⚠️ Cupom inválido. Valor normal será aplicado.")

        token = ""
        if plano_selecionado != "Gratuito":
            token = st.text_input("🔑 Token de Ativação (após pagamento)")

        enviar = st.form_submit_button("Cadastrar")

        if enviar:
            if not nome or not email or not senha:
                st.warning("⚠️ Preencha todos os campos obrigatórios.")
            elif plano_selecionado == "Gratuito":
                try:
                    r = httpx.post(f"{API_URL}/cadastro/gratuito", json={
                        "nome": nome,
                        "email": email,
                        "senha": senha
                    }, timeout=10)
                    if r.status_code == 200:
                        st.success("✅ Cadastro realizado com sucesso!")
                        st.markdown("[🔑 Ir para o login](?login=true)")
                    elif r.status_code == 409:
                        st.warning("⚠️ E-mail já cadastrado.")
                    elif r.status_code == 422:
                        st.warning("⚠️ Dados inválidos. Verifique os campos.")
                    else:
                        st.error(f"Erro inesperado: {r.text}")
                except Exception as e:
                    st.error(f"Erro ao conectar: {e}")
            elif token:
                try:
                    r = httpx.post(f"{API_URL}/cadastro", json={
                        "nome": nome,
                        "email": email,
                        "senha": senha,
                        "token_ativacao": token
                    }, timeout=10)
                    if r.status_code == 200:
                        st.success("✅ Cadastro ativado com sucesso!")
                        st.markdown("[🔑 Ir para o login](?login=true)")
                    else:
                        try:
                            erro = r.json().get("detail", "Erro ao cadastrar.")
                        except Exception:
                            erro = r.text or "Erro ao cadastrar."
                        st.error(f"❌ {erro}")
                except Exception as e:
                    st.error(f"Erro ao conectar: {e}")
            else:
                try:
                    r = httpx.post(f"{API_URL}/api/mercado_pago/criar_preferencia", json={
                        "plano_nome": plano_selecionado,
                        "preco": preco_final
                    }, timeout=10)
                    if r.status_code == 200:
                        pagamento = r.json()
                        st.success("✅ Cadastro iniciado. Finalize o pagamento para receber o token de ativação no e-mail.")
                        st.markdown(f"[🔗 Clique aqui para pagar agora]({pagamento['init_point']})")
                    else:
                        st.error("Erro ao gerar link de pagamento.")
                except Exception as e:
                    st.error(f"Erro ao conectar com Mercado Pago: {e}")

    st.markdown("---")
    if st.button("👨🏻‍💻 Voltar para login"):
        st.query_params = {"login": "true"}
        st.rerun()





# ------------------- SETORES -------------------

def setor_acesso(nome_setor, titulo, conteudo):
    if st.session_state.modo_demo and nome_setor in st.session_state.setores_visitados:
        st.warning("Você já acessou esse setor. Cadastre-se para liberar o uso completo.")
        return
    if st.session_state.modo_demo:
        st.session_state.setores_visitados.append(nome_setor)

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

    dados = {}
    try:
        r = httpx.get(f"{API_URL}/empresa", headers=get_headers())
        if r.status_code == 200:
            dados = r.json()
    except:
        st.warning("Erro ao buscar dados da empresa.")

    nome = st.text_input("Nome da Empresa", value=dados.get("nome_empresa", ""))
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
        titulo = f"👤 {f['nome']} - {f['funcao']}" if f['nome'] else f"👤 Funcionário {i+1}"
        with st.expander(titulo, expanded=st.session_state.funcionario_em_edicao == i):
            nome = st.text_input("Nome", value=f["nome"], key=f"func_nome_{i}")
            nasc = st.text_input("Data de Nascimento", value=f.get("data_nascimento", ""), key=f"func_nasc_{i}")
            funcao = st.text_input("Função", value=f["funcao"], key=f"func_funcao_{i}")
            tel = st.text_input("Telefone", value=f.get("telefone", ""), key=f"func_tel_{i}")
            obs = st.text_area("Observação", value=f.get("observacao", ""), key=f"func_obs_{i}")
            colsalva, colexc = st.columns(2)
            with colsalva:
                if st.button("💾 Salvar", key=f"salvar_func_{i}"):
                    f.update({
                        "nome": nome,
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
        titulo = f"📦 {p['nome']}" if p['nome'] else f"📦 Produto {i+1}"
        with st.expander(titulo, expanded=st.session_state.produto_em_edicao == i):
            nome = st.text_input("Nome do Produto", value=p["nome"], key=f"prod_nome_{i}")
            preco = st.number_input("Preço", value=p["preco"], key=f"prod_preco_{i}", min_value=0.0)
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
                        "nome": nome,
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

    if st.button("Salvar Empresa"):
        payload = {
            "nome_empresa": nome,
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

        try:
            r = httpx.post(f"{API_URL}/empresa", json=payload, headers=get_headers())
            if r.status_code == 200:
                st.success("✅ Empresa salva com sucesso!")
            else:
                st.error("Erro ao salvar empresa.")
                st.error(r.text)
        except Exception as e:
            st.error(f"Erro inesperado: {e}")




def tela_consultoria():
    import os
    # ⚠️ Verificação de acesso: Admin sempre tem acesso total
    email_usuario = st.session_state.get("dados_usuario", {}).get("email", "")
    if email_usuario != "matheus@email.com":
        if not usuario_tem_acesso("consultoria"):
            st.warning("⚠️ Este módulo está disponível apenas para planos pagos.")
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

    from pathlib import Path

    CAMINHO_BASE = Path(__file__).parent  # já está dentro do frontend
    CAMINHO_TOPICOS = CAMINHO_BASE / "data" / "consultoria_topicos_completos.json"
    CAMINHO_SETOR = CAMINHO_BASE / "data" / "topicos_por_setor.json"




    try:
        with open(CAMINHO_TOPICOS, "r", encoding="utf-8") as f:
            topicos = json.load(f)
        with open(CAMINHO_SETOR, "r", encoding="utf-8") as f:
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






def tela_marketing():
    # ⚠️ Verificação de acesso: Admin sempre tem acesso total
    email_usuario = st.session_state.get("dados_usuario", {}).get("email", "")
    if email_usuario != "matheus@email.com":
        if not usuario_tem_acesso("marketing"):
            st.warning("⚠️ Este módulo está disponível apenas para planos pagos.")
            st.stop()

    # 🌐 Estilo global para ocupar toda a tela sem margens
    st.markdown("""
        <style>
            .main .block-container {
                padding-left: 0rem !important;
                padding-right: 0rem !important;
                max-width: 100% !important;
            }
            iframe {
                width: 100% !important;
            }
            header, footer {
                visibility: hidden;
            }
        </style>
    """, unsafe_allow_html=True)


    st.title("📣 Central de Marketing")
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
                <h3 style="margin-bottom: 5px;">📣 Bem-vindo à Central de Marketing</h3>
                <p style="margin: 0; color: #333;">
                    Aqui você encontra campanhas, tendências, datas sazonais e ideias de conteúdo atualizadas com inteligência artificial. É o seu arsenal criativo!
                </p>
                <p style="margin: 0; margin-top: 10px; color: #555;">
                    💡 <strong>Dica do MARK:</strong> Visite esse módulo toda semana para atualizar suas campanhas e manter sua presença digital sempre em alta.
                </p>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

    if not st.session_state.token:
        st.warning("Você precisa estar logado para acessar.")
        return

    headers = get_headers()
    hoje = datetime.date.today()
    ano_atual = hoje.year
    mes_atual = hoje.month

    meses_opcoes = [f"{ano_atual}-{str(m).zfill(2)}" for m in range(1, mes_atual + 1)]
    if hoje.day >= 24:
        proximo_mes = (hoje.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
        meses_opcoes.append(f"{proximo_mes.year}-{str(proximo_mes.month).zfill(2)}")

    mes_escolhido = st.selectbox("🗓 Escolha o mês:", meses_opcoes[::-1])

    try:
        r = httpx.get(f"{API_URL}/marketing/cards/{mes_escolhido}", headers=headers)
        if r.status_code == 200:
            cards_mes = r.json()
        else:
            st.error("Erro ao buscar os cards.")
            return
    except Exception as e:
        st.error(f"Erro ao carregar cards: {e}")
        return

    # Agrupar por tipo
    agrupados = {}
    for card in cards_mes:
        agrupados.setdefault(card["tipo"], []).append(card)

    # Exibir os blocos
    exibir_carrossel("🎯 Campanhas, Datas e Eventos", agrupados.get("Campanha", []), "camp")
    exibir_carrossel("🚀 Tendências e Novidades", agrupados.get("Tendência", []), "tend")
    exibir_carrossel("📦 Produtos em Alta", agrupados.get("Produto", []), "prod")
    exibir_carrossel("📊 Dados e Estatísticas", agrupados.get("Dado", []), "dados")
    exibir_carrossel("🧠 30 Ideias de Conteúdo", agrupados.get("Conteúdo", []), "conteudo")
    exibir_carrossel("💸 Promoções e Ofertas", agrupados.get("Promoção", []), "promo")
    exibir_carrossel("🫶 Campanhas de Conscientização", agrupados.get("Conscientização", []), "conc")

    st.markdown("---")
    if st.button("⭐ Ver Favoritos"):
        try:
            favoritos = httpx.get(f"{API_URL}/marketing/favoritos", headers=headers).json()
            if favoritos:
                st.markdown("## ⭐ Meus Favoritos")
                exibir_carrossel("Favoritos", favoritos, "fav")
            else:
                st.info("Nenhum card foi favoritado ainda.")
        except Exception as e:
            st.warning(f"Erro ao carregar favoritos: {e}")









def tela_branding():
    # ⚠️ Verificação de acesso: Admin sempre tem acesso total
    email_usuario = st.session_state.get("dados_usuario", {}).get("email", "")
    if email_usuario != "matheus@email.com":
        if not usuario_tem_acesso("branding"):
            st.warning("⚠️ Este módulo está disponível apenas para planos pagos.")
            st.stop()

    import base64
    from pathlib import Path

    st.title("🏷️ Central da Marca (Branding)")

    def carregar_imagem_base64(caminho):
        with open(caminho, "rb") as f:
            return base64.b64encode(f.read()).decode()

    CAMINHO_AVATAR = Path(__file__).parent / "img" / "avatar.jpeg"
    avatar_base64 = carregar_imagem_base64(CAMINHO_AVATAR)

    st.markdown(f"""
    <div style="background-color:#ffe9f0; border-left: 6px solid #ff007f; padding: 20px; border-radius: 10px; margin-bottom: 30px;">
        <div style="display: flex; align-items: center;">
            <img src="data:image/jpeg;base64,{avatar_base64}" alt="MARK IA" width="100" style="margin-right: 15px; border-radius: 50%;">
            <div>
                <h3 style="margin-bottom: 5px;">🏷️ Central da Marca</h3>
                <p style="margin: 0; color: #333;">
                    Use as tendências e campanhas da Central de Marketing como base para melhorar o **branding** da sua empresa.
                </p>
                <p style="margin: 0; margin-top: 10px; color: #555;">
                    💡 <strong>Dica do MARK:</strong> Branding é repetição + coerência. Aproveite os momentos em alta para fixar sua marca na mente do cliente.
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.token:
        st.warning("Você precisa estar logado para acessar.")
        return

    headers = get_headers()
    hoje = datetime.date.today()
    ano_atual = hoje.year
    mes_atual = hoje.month

    meses_opcoes = [f"{ano_atual}-{str(m).zfill(2)}" for m in range(1, mes_atual + 1)]
    if hoje.day >= 24:
        proximo_mes = (hoje.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
        meses_opcoes.append(f"{proximo_mes.year}-{str(proximo_mes.month).zfill(2)}")

    mes_escolhido = st.selectbox("🗓 Escolha o mês de referência:", meses_opcoes[::-1])

    try:
        r = httpx.get(f"{API_URL}/marketing/cards/{mes_escolhido}", headers=headers)
        cards_mes = r.json() if r.status_code == 200 else []
    except Exception as e:
        st.error(f"Erro ao buscar cards: {e}")
        return

    def gerar_dicas_branding(titulo_card, descricao_card):
        return f"""
        <ol>
            <li>Reforce a identidade visual da marca nesse tema: use logo, cores e fontes padrão.</li>
            <li>Associe sua marca ao tema “{titulo_card}” com campanhas visuais e parcerias locais.</li>
            <li>Publique depoimentos, bastidores ou ações que fortaleçam os valores da marca.</li>
            <li>Use a campanha para criar lembrança de marca — mencione seu nome em todos os canais.</li>
            <li>Se possível, grave vídeos ou reels com o tema “{titulo_card}” reforçando sua autoridade no assunto.</li>
        </ol>
        """

    def exibir_branding_cards(lista, tipo):
        st.markdown(f"## 🧠 Dicas de Branding para: {tipo}")
        if not lista:
            st.info("Nenhuma sugestão disponível.")
            return

        html = """
        <style>
            .grid-container {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
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
            .card h4 {
                font-size: 16px;
                margin: 0 0 6px;
            }
            .card small {
                color: #999;
                font-size: 12px;
                margin-bottom: 8px;
            }
            .card p {
                font-size: 13px;
                color: #333;
            }
            .card ol {
                font-size: 13px;
                padding-left: 18px;
                margin: 10px 0 0;
            }
        </style>
        <div class="grid-container">
        """
        for card in lista:
            html += f"""
            <div class="card">
                <h4>🏷️ {card['titulo']}</h4>
                <small>📆 Atualizado em: {card['atualizado_em'][:10]}</small>
                <p>{card['descricao']}</p>
                <p><strong>💡 Dicas para Fortalecer sua Marca:</strong></p>
                {gerar_dicas_branding(card['titulo'], card['descricao'])}
            </div>
            """
        html += "</div>"
        components.html(html, height=800 + (len(lista) // 4 * 160), scrolling=True)

    # Agrupar por tipo
    agrupados = {}
    for card in cards_mes:
        agrupados.setdefault(card["tipo"], []).append(card)

    exibir_branding_cards(agrupados.get("Campanha", []), "Campanhas")
    exibir_branding_cards(agrupados.get("Tendência", []), "Tendências")
    exibir_branding_cards(agrupados.get("Promoção", []), "Promoções")
    exibir_branding_cards(agrupados.get("Conscientização", []), "Campanhas do Bem")
    exibir_branding_cards(agrupados.get("Conteúdo", []), "Conteúdos Estratégicos")
    exibir_branding_cards(agrupados.get("Produto", []), "Produtos em Alta")
    exibir_branding_cards(agrupados.get("Dado", []), "Dados e Pesquisas")







def tela_historico():
    st.header("🧠 Histórico")
    usuario_id = st.session_state.dados_usuario.get("id")
    historico = []

    try:
        response = httpx.get(f"{API_URL}/mark/historico", params={"usuario_id": usuario_id})
        if response.status_code == 200:
            historico = response.json()
            if not historico:
                st.info("Nenhuma interação registrada ainda.")
            else:
                for h in historico:
                    st.markdown(f"🕒 *{h['data_envio']}*")
                    st.markdown(f"**{h['remetente']}**: {h['mensagem']}")
                    st.markdown("---")
        else:
            st.error("Erro ao carregar histórico.")
    except Exception as e:
        st.error(f"Erro: {e}")

    # ✅ Botão de exportar histórico em TXT
    if historico:
        conteudo = "\n\n".join(
            [f"{h['data_envio']} - {h['remetente']}: {h['mensagem']}" for h in historico]
        )
        st.download_button(
            "📤 Exportar histórico (.txt)",
            data=conteudo,
            file_name="historico_mark.txt",
            mime="text/plain"
        )










def tela_arquivos():
    # ⚠️ Verificação de acesso: Admin sempre tem acesso total
    email_usuario = st.session_state.get("dados_usuario", {}).get("email", "")
    if email_usuario != "matheus@email.com":
        if not usuario_tem_acesso("arquivo"):
            st.warning("⚠️ Este módulo está disponível apenas para planos pagos.")
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

def tela_mark():
    # ⚠️ Verificação de acesso: Admin sempre tem acesso total
    email_usuario = st.session_state.get("dados_usuario", {}).get("email", "")
    if email_usuario != "matheus@email.com":
        if not usuario_tem_acesso("mark"):
            st.warning("⚠️ Este módulo está disponível apenas para planos pagos.")
            st.stop()

    st.header("🤖 Converse com o MARK")
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
                <h3 style="margin-bottom: 5px;">🤖 Chat Inteligente da MivCast</h3>
                <p style="margin: 0; color: #333;">
                    Converse comigo para tirar dúvidas, criar conteúdos, montar campanhas ou resolver qualquer desafio da sua empresa. Estou conectado aos seus dados reais.
                </p>
                <p style="margin: 0; margin-top: 10px; color: #555;">
                💬 <strong>Dica do MARK:</strong> Use frases diretas como “crie uma legenda para meu produto X” ou “me mostre ideias de reels para meu nicho”.
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

    nome = st.session_state.dados_usuario.get("nome")
    plano = st.session_state.dados_usuario.get("plano_atual", "desconhecido")
    tipo = st.session_state.dados_usuario.get("tipo_usuario", "cliente")
    usuario_id = st.session_state.dados_usuario.get("id")

    st.info(f"Olá, {nome}! Você está no plano **{plano}** como **{tipo}**.")
    st.write("Digite abaixo sua pergunta e o MARK vai te ajudar com base nos dados da sua empresa.")

    pergunta = st.text_input("📩 Sua pergunta:")
    if st.button("Enviar") and pergunta:
        st.session_state.chat.append(("🧑", pergunta))

        try:
            response = httpx.post(
                f"{API_URL}/mark/responder",
                json={"mensagem": pergunta, "usuario_id": usuario_id},
                timeout=60  # aumento de tempo para evitar erro de timeout
            )
            if response.status_code == 200:
                resposta = response.json()["resposta"]
                st.session_state.chat.append(("🤖 MARK", resposta))
            else:
                st.session_state.chat.append(("⚠️", "Erro ao consultar o MARK."))
        except Exception as e:
            st.session_state.chat.append(("❌", f"Erro: {e}"))

    for autor, mensagem in reversed(st.session_state.chat):
        st.markdown(f"**{autor}**: {mensagem}")




# tela_planos()
def tela_planos():
    import httpx
    import streamlit as st

    st.title("📦 Meus Planos")
    plano_atual = st.session_state.dados_usuario.get("plano_atual", "Gratuito")
    usuario_id = st.session_state.dados_usuario.get("id")

    API_URL = "https://mivmark-backend.onrender.com"
    try:
        planos = httpx.get(f"{API_URL}/planos/").json()
    except:
        st.error("Erro ao buscar planos.")
        return

    usuario = st.session_state.get("dados_usuario", {})
    plano_atual = usuario.get("plano_atual") or "Gratuito"
    if usuario.get("is_admin"):
        plano_atual = "Administrador (acesso total)"

    st.markdown(f"""
    <div style='background-color:#f0f8ff; padding: 15px; border-left: 6px solid #007bff; border-radius: 8px; margin-bottom: 20px;'>
        <strong>🔒 Seu plano atual:</strong> <span style='font-size:18px; color:#007bff'>{plano_atual}</span><br>
        Para liberar mais recursos do sistema, você pode fazer upgrade agora mesmo.
    </div>
    """, unsafe_allow_html=True)

    st.subheader("🚀 Planos Disponíveis")
    colunas = st.columns(4)

    cupons_validos = {
        "BEMVINDO10": ("porcentagem", 10),
        "MIV99": ("porcentagem", 90),
        "PROMO25": ("porcentagem", 25),
        "VIP50": ("fixo", 50),
        "R10OFF": ("fixo", 10)
    }

    for i, plano in enumerate(planos):
        with colunas[i % 4]:
            destaques = "".join([f"<li>{m}</li>" for m in plano['modulos_liberados']])
            st.markdown(f"""
            <div style='border: 1px solid #ccc; border-radius: 10px; padding: 20px; margin-bottom: 20px;'>
                <h4>{plano['nome']}</h4>
                <p>{plano['descricao']}</p>
                <ul>{destaques}</ul>
                <p><strong>💰 R$ {plano['preco_mensal']:.2f}/mês</strong></p>
            """, unsafe_allow_html=True)

            cupom_input = st.text_input(f"Digite um cupom para {plano['nome']}", key=f"cupom_{plano['id']}").upper()

            if plano['nome'] != plano_atual:
                if st.button(f"Quero esse plano: {plano['nome']}", key=f"contratar_{plano['id']}"):
                    preco = plano['preco_mensal']
                    desconto = 0

                    if cupom_input and cupom_input in cupons_validos:
                        tipo, valor = cupons_validos[cupom_input]
                        if tipo == "porcentagem":
                            desconto = preco * (valor / 100)
                        elif tipo == "fixo":
                            desconto = valor
                        preco -= desconto
                        preco = max(0, round(preco, 2))
                        st.success(f"🎉 Cupom aplicado! Novo valor: R$ {preco:.2f}")
                    elif cupom_input:
                        st.warning("⚠️ Cupom inválido. Será cobrado o valor original.")

                    try:
                        resposta = httpx.post(f"{API_URL}/api/mercado_pago/criar_preferencia", json={
                            "plano_nome": plano["nome"],
                            "preco": preco
                        })
                        if resposta.status_code == 200:
                            pagamento = resposta.json()
                            st.markdown(f"[🔗 Clique aqui para pagar agora]({pagamento['init_point']})")
                        else:
                            st.error("Erro ao gerar link de pagamento.")
                    except Exception as e:
                        st.error(f"Erro ao conectar com Mercado Pago: {e}")
            else:
                st.info("✅ Esse já é seu plano atual.")
            st.markdown("</div>", unsafe_allow_html=True)





def painel_admin():
    st.title("⚙️ Painel Administrativo")
    abas = st.tabs(["🎓 Cursos", "🎟 Tokens", "👥 Usuários", "📱 Aplicativos", "🧩 Planos"])

    # -------- CURSOS --------
    with abas[0]:
        painel_admin_cursos()

    # -------- TOKENS --------
    with abas[1]:
        st.subheader("Gerar Token de Ativação")
        senha_admin = st.text_input("Senha Admin", type="password", key="senha_token")

        if st.button("Gerar Token"):
            try:
                response = httpx.post(f"{API_URL}/admin/gerar_token", params={"senha_admin": senha_admin})
                if response.status_code == 200:
                    token = response.json()["token_ativacao"]
                    st.success(f"✅ Token gerado: `{token}`")
                else:
                    st.error(response.json().get("detail", "Erro ao gerar token"))
            except Exception as e:
                st.error(f"Erro: {e}")

        st.divider()
        st.subheader("🔎 Tokens Gerados")
        if st.button("🔄 Atualizar lista de tokens"):
            try:
                response = httpx.get(f"{API_URL}/admin/listar_tokens", params={"senha_admin": senha_admin})
                if response.status_code == 200:
                    tokens = response.json()
                    if tokens:
                        for t in tokens:
                            status = "🟢 Ativo" if t["ativo"] else "❌ Usado"
                            data = t["data_criacao"] or "N/A"
                            st.markdown(f"`{t['token']}` • {status} • Criado em {data}")
                    else:
                        st.info("Nenhum token encontrado.")
                else:
                    st.error("Erro ao buscar tokens.")
            except Exception as e:
                st.error(f"Erro: {e}")

    # -------- USUÁRIOS --------
    with abas[2]:
        st.subheader("👥 Usuários Cadastrados")
        if st.button("🔄 Ver usuários cadastrados"):
            try:
                response = httpx.get(
                    f"{API_URL}/admin/usuarios",
                    params={"senha_admin": st.session_state.get("senha_token", "")}
                )
                if response.status_code == 200:
                    usuarios = response.json()
                    if usuarios:
                        for u in usuarios:
                            nome = u["nome"]
                            email = u["email"]
                            plano = u.get("plano_atual", "nenhum")
                            tipo = u.get("tipo_usuario", "cliente")
                            data = u.get("data_criacao", "N/A")
                            st.markdown(
                                f"📛 **{nome}**  \n📧 `{email}`  \n📦 Plano: `{plano}` • Tipo: `{tipo}` • Criado em: {data}"
                            )
                            st.markdown("---")
                    else:
                        st.info("Nenhum usuário encontrado.")
                else:
                    st.error("Erro ao buscar usuários.")
            except Exception as e:
                st.error(f"Erro: {e}")

    # -------- APLICATIVOS --------
    with abas[3]:
        st.subheader("📱 Gerenciar Aplicativos")
        listar_aplicativos_admin()


    with abas[4]:
        aba_gerenciar_planos()





def painel_admin_cursos():
    st.title("📚 Painel de Cursos")

    # Modo Edição de Curso
    if st.session_state.get("modo_edicao") and st.session_state.get("curso_editando"):
        st.subheader("✏️ Editar Curso")

        curso = st.session_state["curso_editando"]

        titulo = st.text_input("Título", value=curso["titulo"])
        descricao = st.text_area("Descrição", value=curso["descricao"])
        capa_url = st.text_input("URL da Capa", value=curso["capa_url"])
        categoria = st.text_input("Categoria", value=curso["categoria"])
        gratuito = st.checkbox("Gratuito", value=curso["gratuito"])
        preco = st.number_input("Preço", value=curso.get("preco") or 0.0, disabled=gratuito)
        destaque = st.checkbox("Destaque", value=curso["destaque"])

        if st.button("💾 Salvar Alterações"):
            payload = {
                "titulo": titulo,
                "descricao": descricao,
                "capa_url": capa_url,
                "categoria": categoria,
                "gratuito": gratuito,
                "preco": preco if not gratuito else None,
                "destaque": destaque,
                "ativo": True
            }
            try:
                r = httpx.put(f"{API_URL}/cursos/{curso['id']}", json=payload)
                if r.status_code == 200:
                    st.success("Curso atualizado com sucesso!")
                    st.session_state["modo_edicao"] = False
                    st.session_state["curso_editando"] = None
                    st.rerun()
                else:
                    st.error("Erro ao atualizar curso.")
            except Exception as e:
                st.error(f"Erro ao conectar com servidor: {e}")

        if st.button("❌ Cancelar"):
            st.session_state["modo_edicao"] = False
            st.session_state["curso_editando"] = None
            st.rerun()

        st.stop()

    # Cadastro de Curso Novo
    st.subheader("➕ Adicionar novo curso")

    titulo = st.text_input("Título do Curso")
    descricao = st.text_area("Descrição")
    capa = st.text_input("URL da Imagem de Capa")
    categoria = st.text_input("Categoria")
    gratuito = st.checkbox("Gratuito", value=True)
    preco = st.number_input("Preço", min_value=0.0, step=0.01, disabled=gratuito)
    destaque = st.checkbox("Destacar no topo", value=False)

    if st.button("Salvar Curso"):
        payload = {
            "titulo": titulo,
            "descricao": descricao,
            "capa_url": capa,
            "categoria": categoria,
            "gratuito": gratuito,
            "preco": preco if not gratuito else None,
            "destaque": destaque,
            "ativo": True
        }
        try:
            r = httpx.post(f"{API_URL}/cursos/admin/curso", json=payload)
            if r.status_code == 200:
                st.success("Curso cadastrado com sucesso!")
            else:
                st.error("Erro ao salvar curso.")
        except Exception as e:
            st.error(f"Erro: {e}")

    st.divider()
    st.subheader("🎞 Adicionar Aula a um Curso")

    cursos = httpx.get(f"{API_URL}/cursos/").json()
    nomes_cursos = {f"{c['titulo']} (ID {c['id']})": c['id'] for c in cursos}
    curso_escolhido = st.selectbox("Curso", list(nomes_cursos.keys()))
    id_curso_aula = nomes_cursos[curso_escolhido]
    titulo_aula = st.text_input("Título da Aula")
    descricao_aula = st.text_area("Descrição da Aula")
    video = st.text_input("Link do vídeo (YouTube)")
    ordem = st.number_input("Ordem", step=1)

    if st.button("Salvar Aula"):
        payload = {
            "curso_id": id_curso_aula,
            "titulo": titulo_aula,
            "descricao": descricao_aula,
            "video_url": video,
            "ordem": ordem
        }
        try:
            r = httpx.post(f"{API_URL}/cursos/admin/aula", json=payload)
            if r.status_code == 200:
                st.success("Aula salva com sucesso!")
            else:
                st.error("Erro ao salvar aula.")
        except Exception as e:
            st.error(f"Erro: {e}")

    st.divider()
    st.subheader("🎟 Criar Cupom de Desconto")

    codigo = st.text_input("Código do Cupom")
    descricao_cupom = st.text_input("Descrição breve")
    percentual = st.number_input("Desconto (%)", min_value=1.0, max_value=100.0, step=0.5)
    id_curso_cupom = st.number_input("ID do Curso (ou 0 para todos)", step=1)
    validade = st.date_input("Validade (opcional)")

    if st.button("Criar Cupom"):
        payload = {
            "codigo": codigo,
            "descricao": descricao_cupom,
            "percentual": percentual,
            "curso_id": id_curso_cupom if id_curso_cupom > 0 else None,
            "validade": str(validade) if validade else None
        }
        try:
            r = httpx.post(f"{API_URL}/cursos/admin/cupom", json=payload)
            if r.status_code == 200:
                st.success("Cupom criado com sucesso!")
            else:
                st.error("Erro ao criar cupom.")
        except Exception as e:
            st.error(f"Erro: {e}")

    st.divider()
    st.subheader("📚 Cursos Existentes")

    try:
        r = httpx.get(f"{API_URL}/cursos/")
        if r.status_code == 200:
            cursos = r.json()
            for curso in cursos:
                with st.expander(f"{curso['titulo']}"):
                    st.markdown(f"**Categoria:** {curso['categoria']}")
                    st.markdown(f"**Gratuito:** {'Sim' if curso['gratuito'] else 'Não'}")
                    if not curso["gratuito"]:
                        st.markdown(f"**Preço:** R$ {curso['preco']:.2f}")
                    st.markdown(f"**Destaque:** {'Sim' if curso['destaque'] else 'Não'}")

                    if st.button(f"✏️ Editar {curso['id']}", key=f"editar_{curso['id']}"):
                        st.session_state["curso_editando"] = curso
                        st.session_state["modo_edicao"] = True
                        st.rerun()
        else:
            st.warning("Não foi possível carregar os cursos.")
    except Exception as e:
        st.error(f"Erro ao buscar cursos: {e}")



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
        st.warning("⚠️ Este módulo está disponível apenas para planos pagos.")
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

            if curso["gratuito"] or curso["id"] in st.session_state.get("cursos_liberados", []):
                if st.button("▶️ Acessar", key=f"acessar_{curso['id']}"):
                    st.session_state["curso_selecionado"] = curso["id"]
                    st.rerun()
            else:
                if st.button("💳 Comprar", key=f"comprar_{curso['id']}"):
                    st.session_state["curso_checkout"] = curso["id"]
                    st.rerun()


def tela_checkout(curso_id):
    try:
        r = httpx.get(f"{API_URL}/cursos/{curso_id}", headers=get_headers())
        curso = r.json()
    except:
        st.error("Erro ao buscar curso.")
        return

    st.title("💳 Checkout do Curso")
    st.subheader(curso["titulo"])
    st.image(curso["capa_url"], use_container_width=True)
    st.write(curso["descricao"])

    preco = curso["preco"] or 0.0
    preco_final = preco
    desconto = 0.0
    cupom_aplicado = False

    st.markdown("### 🎟 Aplicar Cupom de Desconto")
    codigo = st.text_input("Digite o código do cupom")
    if st.button("Validar Cupom"):
        try:
            r = httpx.get(f"{API_URL}/cursos/cupom/{codigo}")
            if r.status_code == 200:
                cupom = r.json()
                desconto = (cupom["percentual"] / 100.0) * preco
                preco_final = preco - desconto
                st.success(f"✅ Cupom aplicado: {cupom['descricao']} (-{cupom['percentual']}%)")
                cupom_aplicado = True
            else:
                st.error("❌ Cupom inválido ou expirado")
        except Exception as e:
            st.error(f"Erro ao validar cupom: {e}")

    st.markdown("---")
    st.markdown("### 💰 Formas de Pagamento")
    valor_pix = preco_final * 0.9
    st.markdown(f"💸 **PIX (10% OFF):** R$ {valor_pix:.2f}")
    st.markdown(f"💳 **Cartão até 6x sem juros** ou até 12x com juros")
    st.markdown(f"🧾 **Total com desconto aplicado:** R$ {preco_final:.2f}")

    if st.button("Finalizar Compra"):
        st.success("✅ Compra simulada com sucesso! Acesso liberado.")
        if "cursos_liberados" not in st.session_state:
            st.session_state["cursos_liberados"] = []
        st.session_state["cursos_liberados"].append(curso_id)
        st.session_state["curso_liberado"] = curso_id
        st.session_state["curso_checkout"] = None
        st.rerun()

    if st.button("⬅️ Cancelar e voltar"):
        st.session_state["curso_checkout"] = None
        st.rerun()

    if st.button("⬅️ Voltar para Cursos"):
        st.session_state.pop("curso_checkout", None)
        st.session_state.pop("curso_espiar", None)
        st.rerun()




def tela_detalhe_curso(curso_id):
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
    st.subheader("🎥 Aulas disponíveis")

    aulas_concluidas = []
    try:
        p = httpx.get(f"{API_URL}/cursos/progresso", headers=get_headers())
        aulas_concluidas = p.json().get("aulas_concluidas", [])
    except:
        pass

    for aula in sorted(curso["aulas"], key=lambda a: a["ordem"]):
        concluida = aula["id"] in aulas_concluidas
        st.markdown(f"#### {aula['titulo']}")
        st.write(aula["descricao"])
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
        st.session_state.pop("curso_checkout", None)
        st.session_state.pop("curso_espiar", None)
        st.rerun()







def get_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}

def tela_aplicativos():
    if not usuario_tem_acesso("aplicativos"):
        st.warning("⚠️ Este módulo está disponível apenas para planos pagos.")
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
    st.title("📲 Meus Aplicativos")

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





# ------------------- INTERFACE PRINCIPAL -------------------

API_URL = "https://mivmark-backend.onrender.com"

def get_headers():
    """Gera o cabeçalho com token salvo"""
    return {"Authorization": f"Bearer {st.session_state.get('token', '')}"}

def obter_dados_usuario():
    """Consulta os dados do usuário logado e salva no session_state"""
    try:
        response = httpx.get(f"{API_URL}/minha-conta", headers=get_headers())
        if response.status_code == 200:
            st.session_state["dados_usuario"] = response.json()
        else:
            st.error("❌ Erro ao obter dados do usuário.")
            st.session_state["token"] = None
            st.session_state["dados_usuario"] = {}
    except Exception as e:
        st.error(f"❌ Erro ao consultar perfil: {e}")
        st.session_state["token"] = None
        st.session_state["dados_usuario"] = {}

def main():
    st.set_page_config(page_title="MARK Sistema IA", layout="wide")

    query_params = st.query_params
    modo_cadastro = "cadastro" in query_params
    logado = st.session_state.token or st.session_state.modo_demo

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
        obter_dados_usuario()
        usuario = st.session_state.dados_usuario
        plano = usuario.get("plano_atual") or "Gratuito"

        logo_url = usuario.get("logo_url")
        if logo_url:
            st.sidebar.image(logo_url, use_container_width=True)
        else:
            st.sidebar.markdown("📌 Sua logo aparecerá aqui")

        if usuario.get("is_admin"):
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

    if st.session_state.admin:
        painel_admin()
        if st.button("⬅️ Voltar para o sistema"):
            st.session_state.admin = False
            st.rerun()
        return

    if st.session_state.get("curso_checkout"):
        from frontend.cursos import tela_checkout
        tela_checkout(st.session_state["curso_checkout"])
        return

    if st.session_state.get("curso_liberado"):
        from frontend.cursos import tela_curso
        tela_curso(st.session_state["curso_liberado"])
        return

    if st.session_state.get("curso_espiar"):
        from frontend.cursos import tela_detalhe_curso
        tela_detalhe_curso(st.session_state["curso_espiar"])
        return

    st.sidebar.title("📚 Menu")
    escolha = st.sidebar.radio("Navegar para:", [
        "🏠 **Início**",
        "💳 Plano Atual",
        "🏢 **Empresa**",
        "❤️ **Saúde da Empresa**",
        "📋 **Consultoria**",
        "🎓 **Cursos**",
        "📘 **Meus Cursos**",
        "📱 **Aplicativos**",
        "💰 **Orçamento**",
        "📅 **Agenda**",
        "📣 **Central de Marketing**",
        "🏷️ **Central da Marca (Branding)**",
        "🧠 **Histórico**",
        "📁 **Arquivos**",
        "🤖 **MARK IA**",
        "🌐 **Página e Chat do Cliente**",
        "🚪 **Sair**"
    ])

    if escolha == "🏠 **Início**":
        tela_inicio()
    elif escolha == "💳 Plano Atual":
        tela_planos()
    elif escolha == "🏢 **Empresa**":
        tela_empresa()
    elif escolha == "❤️ **Saúde da Empresa**":
        from frontend.saude_empresa import tela_saude_empresa
        tela_saude_empresa()
    elif escolha == "📋 **Consultoria**":
        tela_consultoria()
    elif escolha == "🎓 **Cursos**":
        from frontend.cursos import tela_cursos
        tela_cursos()
    elif escolha == "📘 **Meus Cursos**":
        from frontend.cursos import tela_meus_cursos
        tela_meus_cursos()
    elif escolha == "📱 **Aplicativos**":
        from frontend.aplicativos import tela_aplicativos
        tela_aplicativos()
    elif escolha == "📲 **Meus Apps**":
        from frontend.aplicativos import tela_meus_aplicativos
        tela_meus_aplicativos()
    elif escolha == "💰 **Orçamento**":
        from frontend.orcamento import tela_orcamento
        try:
            r = httpx.get(f"{API_URL}/empresa", headers=get_headers())
            dados_empresa = r.json() if r.status_code == 200 else {}
        except Exception as e:
            dados_empresa = {}
            st.error(f"Erro ao buscar dados da empresa: {e}")
        tela_orcamento(dados_empresa)
    elif escolha == "📅 **Agenda**":
        tela_agenda()
    elif escolha == "📣 **Central de Marketing**":
        tela_marketing()
    elif escolha == "🏷️ **Central da Marca (Branding)**":
        tela_branding()
    elif escolha == "🧠 **Histórico**":
        tela_historico()
    elif escolha == "📁 **Arquivos**":
        tela_arquivos()
    elif escolha == "🤖 **MARK IA**":
        tela_mark()
    elif escolha == "🌐 **Página e Chat do Cliente**":
        tela_site_cliente()
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

