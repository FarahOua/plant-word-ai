import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

BACKEND_URL = os.getenv("BACKEND_URL").rstrip("/")
ANALYZE_ENDPOINT = f"{BACKEND_URL}/api/analyze"
HEALTH_ENDPOINT = f"{BACKEND_URL}/api/health"
CHAT_ENDPOINT = f"{BACKEND_URL}/api/chat"
EVAL_CASES_ENDPOINT = f"{BACKEND_URL}/api/evaluation/cases"
EVAL_RUN_ENDPOINT = f"{BACKEND_URL}/api/evaluation/run"
EVAL_FEEDBACK_ENDPOINT = f"{BACKEND_URL}/api/evaluation/feedback"

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
# Un cas d'évaluation = appel du workflow n8n + appel du juge LLM
EVAL_TIMEOUT = int(os.getenv("EVAL_TIMEOUT", "150"))

ACCEPTED_TYPES = ["jpg", "jpeg", "png"]
