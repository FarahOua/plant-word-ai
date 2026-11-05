import requests

from config import ANALYZE_ENDPOINT, CHAT_ENDPOINT, HEALTH_ENDPOINT, REQUEST_TIMEOUT


class ApiError(Exception):
    """Erreur lors de la communication avec l'API."""


def check_backend() -> bool:
    """Renvoie True si l'API répond."""
    try:
        return requests.get(HEALTH_ENDPOINT, timeout=3).ok
    except requests.RequestException:
        return False


def _post(url: str, **kwargs) -> dict:
    """Envoie une requête POST et renvoie la réponse JSON, ou lève ApiError."""
    try:
        response = requests.post(url, timeout=REQUEST_TIMEOUT, **kwargs)
    except requests.ConnectionError:
        raise ApiError("Impossible de joindre le backend.")
    except requests.Timeout:
        raise ApiError("Le backend met trop de temps à répondre.")
    except requests.RequestException as error:
        raise ApiError(f"Erreur réseau : {error}")

    try:
        data = response.json()
    except ValueError:
        raise ApiError(f"Réponse invalide du backend (HTTP {response.status_code}).")

    if not response.ok:
        raise ApiError(data.get("error", f"Erreur HTTP {response.status_code}"))

    return data


def analyze(filename: str, content: bytes, mime_type: str) -> dict:
    """Envoie l'image à /api/analyze et renvoie la réponse JSON."""
    return _post(ANALYZE_ENDPOINT, files={"image": (filename, content, mime_type)})


def chat(
    session_id: str, message: str, analysis: dict, history: list[dict], location: dict | None = None
) -> str:
    """Envoie une question au chatbot avec le résultat de l'analyse et renvoie sa réponse.

    `session_id` : identifiant de la conversation, utilisé par n8n pour retrouver l'historique.
    `location` (facultatif) : commune choisie, {"city", "department", "lat", "lon"}.
    """
    body = {"session_id": session_id, "message": message, "analysis": analysis, "history": history}
    if location:
        body["location"] = {k: location[k] for k in ("city", "department", "lat", "lon")}
    data = _post(CHAT_ENDPOINT, json=body)
    return data["reply"]
