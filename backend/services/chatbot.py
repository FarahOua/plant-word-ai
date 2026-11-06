"""Service chatbot PlantWorld AI connecté à n8n."""

import requests
from flask import current_app


class ChatbotUnavailableError(RuntimeError):
    """Le workflow n8n est indisponible ou renvoie une réponse invalide."""


def build_context(analysis: dict) -> str:
    """Résume le diagnostic de classification."""
    if not analysis.get("recognized"):
        return "Plante non reconnue."
    if analysis.get("is_healthy"):
        return f"Plante : {analysis['plant']}, saine."
    return f"Plante : {analysis['plant']}, maladie : {analysis['disease']}."


def build_payload(session_id: str, message: str, analysis: dict) -> dict:
    """Construit le body envoyé au webhook n8n."""
    payload = {
        "sessionId": session_id,
        "message": message,
        "context": build_context(analysis),
        "analysis": {
            k: analysis.get(k)
            for k in (
                "recognized",
                "label",
                "plant",
                "disease",
                "is_healthy",
                "confidence",
            )
        },
    }

    return payload


def send_to_n8n(payload: dict) -> str:
    """Envoie le body au webhook n8n et renvoie la réponse de l'agent IA."""
    webhook_url = current_app.config["N8N_WEBHOOK_URL"]
    timeout = current_app.config["N8N_TIMEOUT"]
    api_key = current_app.config["N8N_API_KEY"]

    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()

    except (requests.RequestException, ValueError) as error:
        raise ChatbotUnavailableError(
            f"Erreur de communication avec n8n : {error}"
        ) from error

    if data.get("success") is not True:
        raise ChatbotUnavailableError("Le workflow n8n a signalé un échec.")

    answer = data.get("answer")

    if not isinstance(answer, str) or not answer.strip():
        raise ChatbotUnavailableError("Réponse vide ou invalide de n8n.")

    return answer


def generate_reply(
    session_id: str,
    message: str,
    analysis: dict,
    history: list[dict],
) -> str:
    """Envoie la question à n8n et récupère la réponse de l'agent IA."""
    return send_to_n8n(build_payload(session_id, message, analysis))
