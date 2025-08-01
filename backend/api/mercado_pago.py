from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

router = APIRouter()

@router.post("/mercado-pago/webhook")
async def webhook_mercado_pago(request: Request):
    payload = await request.json()
    print("🔔 Webhook recebido:", payload)

    # Verificação básica de evento
    if payload.get("type") == "payment":
        data_id = payload.get("data", {}).get("id")
        # Aqui você poderá consultar a API do Mercado Pago usando o ID do pagamento
        # Verificar se está aprovado, identificar o curso e liberar acesso ao aluno

        # Exemplo fictício:
        # liberar_curso_para_usuario(order_id, curso_id)

    return JSONResponse(content={"status": "ok"})
