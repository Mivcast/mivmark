import httpx
import streamlit as st

API_URL = "https://mivmark-backend.onrender.com"  # ajuste se for ambiente online

def usuario_tem_acesso(modulo: str) -> bool:
    usuario = st.session_state.get("dados_usuario", {})
    plano = usuario.get("plano_atual")

    # ✅ Se for o administrador, libera acesso total
    if usuario.get("email") == "matheus@email.com":
        return True

    if not plano:
        return False

    try:
        r = httpx.get(f"{API_URL}/planos/")
        if r.status_code == 200:
            planos = r.json()
            for p in planos:
                if p["nome"].lower() == plano.lower():
                    return modulo in p.get("modulos_liberados", [])
    except Exception as e:
        st.warning(f"Erro ao verificar acesso ao módulo: {e}")

    return False
