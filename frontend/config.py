import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

BACKEND_URL = os.getenv("BACKEND_URL").rstrip("/")
ANALYZE_ENDPOINT = f"{BACKEND_URL}/api/analyze"
HEALTH_ENDPOINT = f"{BACKEND_URL}/api/health"
CHAT_ENDPOINT = f"{BACKEND_URL}/api/chat"

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))

ACCEPTED_TYPES = ["jpg", "jpeg", "png"]
