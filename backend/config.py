import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


class Config:
    # Serveur
    HOST = os.getenv("BACKEND_HOST")
    PORT = int(os.getenv("BACKEND_PORT"))
    DEBUG = os.getenv("FLASK_DEBUG") == "1"

    # Upload : taille maximale acceptée (10 Mo par défaut)
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_MB")) * 1024 * 1024


    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
    ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG"}

    # Modèle de détection des maladies (Hugging Face, entraîné sur PlantVillage)
    MODEL_NAME = os.getenv("MODEL_NAME")
    # Version figée du modèle : mêmes résultats même si l'auteur le modifie (vide = dernière version)
    MODEL_REVISION = os.getenv("MODEL_REVISION") or None
    MODEL_DEVICE = os.getenv("MODEL_DEVICE")
    MODEL_PRELOAD = os.getenv("MODEL_PRELOAD") == "1"

    # En dessous de ce seuil, la plante est considérée comme non reconnue
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD"))
    TOP_K = int(os.getenv("TOP_K"))

    # Chatbot : limites des requêtes reçues par /api/chat
    CHAT_MAX_MESSAGE_LENGTH = 2000  # caractères par message
    CHAT_MAX_HISTORY = 50           # messages précédents transmis

    # Chatbot : workflow n8n (RAG + LLM)
    N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")
    N8N_API_KEY = os.getenv("N8N_API_KEY", "")
    N8N_TIMEOUT = int(os.getenv("N8N_TIMEOUT"))  # secondes

    # Évaluation : LLM juge (API compatible OpenAI, ex. LiteLLM). Vide = juge désactivé.
    JUDGE_BASE_URL = os.getenv("JUDGE_BASE_URL", "")
    JUDGE_API_KEY = os.getenv("JUDGE_API_KEY", "")
    JUDGE_MODEL = os.getenv("JUDGE_MODEL") or "openai/gpt-4.1-mini"
