from dotenv import load_dotenv
from pathlib import Path

# Caminho absoluto da pasta raiz do projeto
load_dotenv(dotenv_path=Path("C:/Projetos/mivmark/.env"))

import os
print(os.getenv("DATABASE_URL"))  # Só para testar