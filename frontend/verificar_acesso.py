import httpx
import streamlit as st

API_URL = "https://mivmark-backend.onrender.com"

def usuario_tem_acesso(modulo: str) -> bool:
    usuario = st.session_state.get("dados_usuario", {}) or {}

    # ✅ 1) Administrador SEMPRE tem acesso total
    if usuario.get("tipo_usuario") == "admin":
        return True

    # ✅ 2) Seu e-mail pessoal também tem acesso total (se quiser manter)
    email = (usuario.get("email") or "").strip().lower()
    if email == "matheus@email.com":
        return True

    # ✅ 3) Demais usuários seguem a regra de plano
    plano = usuario.get("plano_atual")
    if not plano:
        return False

    # Compatibilidade: se vier "consultoria_full", trata como "Profissional"
    if str(plano).lower() == "consultoria_full":
        plano = "Profissional"

    try:
        r = httpx.get(f"{API_URL}/planos/")
        if r.status_code == 200:
            planos = r.json()
            for p in planos:
                if p["nome"].lower() == str(plano).lower():
                    return modulo in p.get("modulos_liberados", [])
    except Exception as e:
        st.warning(f"Erro ao verificar acesso ao módulo: {e}")

    return False
