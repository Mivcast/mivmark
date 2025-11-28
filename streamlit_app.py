import sys
import os

# Garante que a pasta frontend seja encontrada
sys.path.append(os.path.join(os.path.dirname(__file__), "frontend"))

from frontend.app import main

if __name__ == "__main__":
    main()
