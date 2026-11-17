import os
from dotenv import load_dotenv

load_dotenv()

# Ollama 설정
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3.1")
EMBED_MODEL = os.getenv("EMBED_MODEL", "bge-m3")
