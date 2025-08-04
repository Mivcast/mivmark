@echo off
cd /d %~dp0

:: Garante que o .env da raiz será carregado corretamente
set PYTHONPATH=.

:: Abre o backend com o .env no contexto correto
start "Backend" cmd /k "uvicorn backend.main:app --reload"

:: Aguarda 2 segundos para o backend subir
timeout /t 2 /nobreak >nul

:: Abre o frontend (Streamlit) em outro terminal
start "Frontend" cmd /k "streamlit run frontend/app.py"

exit
