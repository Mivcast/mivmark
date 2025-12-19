import os
import httpx
import streamlit as st

API_URL = (os.getenv("API_URL") or "https://mivmark-backend.onrender.com").strip().rstrip("/")

# ✅ Aliases para evitar cascata de erros (nomes antigos -> nomes novos)
ALIASES = {
    # Arquivos
    "arquivos": "arquivo",
    "arquivo": "arquivo",

    # MARK / Chat
    "chat": "mark",
    "mark_ia": "mark",
    "mark": "mark",

    # Site e Chat
    "site": "site_chat",
    "site_cliente": "site_chat",
    "site_e_chat": "site_chat",
    "site-chat": "site_chat",
    "site_chat": "site_chat",

    # Consultor mensal
    "consultor": "consultor_mensal",
    "consultor-mensal": "consultor_mensal",
    "consultor_mensal": "consultor_mensal",

    # Outros (mantém o mesmo)
    "empresa": "empresa",
    "saude": "saude",
    "consultoria": "consultoria",
    "cursos": "cursos",
    "aplicativos": "aplicativos",
    "orcamento": "orcamento",
    "agenda": "agenda",
}

def _norm_mod(m: str) -> str:
    m = (m or "").strip().lower()
    return ALIASES.get(m, m)

def planos_que_liberam(modulo: str) -> list[str]:
    modulo_norm = _norm_mod(modulo)
    try:
        r = httpx.get(f"{API_URL}/planos/")
        if r.status_code == 200:
            planos = r.json()
            liberam = []
            for p in planos:
                mods = {_norm_mod(x) for x in (p.get("modulos_liberados") or [])}
                if modulo_norm in mods:
                    liberam.append(p.get("nome"))
            return liberam
    except:
        pass
    return []


def usuario_tem_acesso(modulo: str) -> bool:
    usuario = st.session_state.get("dados_usuario", {}) or {}
    modulo_norm = _norm_mod(modulo)

    # ✅ 1) Administrador SEMPRE tem acesso total
    if usuario.get("tipo_usuario") == "admin":
        return True

    # ✅ 2) Seu e-mail pessoal também tem acesso total (se quiser manter)
    email = (usuario.get("email") or "").strip().lower()
    if email == "matheus@email.com":
        return True

    # ✅ 3) Plano atual do usuário
    plano = usuario.get("plano_atual") or "Gratuito"

    # (se você ainda usa esse legado)
    if str(plano).lower() == "consultoria_full":
        plano = "Profissional"

    try:
        r = httpx.get(f"{API_URL}/planos/")
        if r.status_code == 200:
            planos = r.json()
            for p in planos:
                if (p.get("nome") or "").strip().lower() == str(plano).strip().lower():
                    modulos_plano = p.get("modulos_liberados", []) or []
                    # Normaliza módulos do plano também (aceita nomes antigos)
                    modulos_norm = {_norm_mod(x) for x in modulos_plano}
                    return modulo_norm in modulos_norm
    except Exception as e:
        st.warning(f"Erro ao verificar acesso ao módulo: {e}")

    return False
