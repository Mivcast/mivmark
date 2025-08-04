# MivMark

Sistema de consultoria, marketing e automação para empresas.

## Estrutura

- `/backend` - API FastAPI (login, cadastros, banco de dados, IA)
- `/frontend` - Interface com Streamlit
- `/templates_html` - Modelos para sites do cliente
- `/data` - Orçamentos, arquivos, histórico

## Como rodar local:

### Backend
```bash
cd backend
uvicorn main:app --reload
