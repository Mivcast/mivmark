import os
import time
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

inicio = time.perf_counter()

resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Teste rápido"}]
)

fim = time.perf_counter()

print("Tempo OpenAI direto:", round(fim - inicio, 2), "s")
print("Resposta:", resp.choices[0].message.content)
