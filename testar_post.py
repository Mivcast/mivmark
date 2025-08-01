import requests

url = "http://127.0.0.1:8000/mark/responder"
payload = {
    "mensagem": "MARK, o que você faz?",
    "usuario_id": 1
}

response = requests.post(url, json=payload)
print(response.status_code)
print(response.json())