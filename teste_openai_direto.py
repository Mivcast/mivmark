from openai import OpenAI

openai.api_key = os.getenv("OPENAI_API_KEY")

try:
    resposta = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Olá Mark, você está funcionando?"}],
        timeout=60
    )
    print("✅ Resposta da IA:")
    print(resposta.choices[0].message.content)
except Exception as e:
    print("❌ Erro ao chamar a IA:", e)