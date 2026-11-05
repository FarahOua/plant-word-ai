"""Logique du chatbot.

Le chatbot discute de l'image analysée à partir du résultat de l'analyse
(il ne voit pas la photo elle-même).

Pour l'instant, generate_reply() renvoie une réponse fictive. Pour brancher
un vrai moteur (RAG via n8n, LLM...), il suffit de remplacer son contenu :
build_context() fournit déjà le diagnostic sous forme de texte, prêt à être
placé dans le prompt.
"""

import json


class ChatbotUnavailableError(RuntimeError):
    """Le workflow n8n est injoignable ou a renvoyé une réponse inutilisable."""


def build_context(analysis: dict) -> str:
    """Résume le diagnostic en une phrase pour le prompt du LLM."""
    if not analysis.get("recognized"):
        return "Plante non reconnue."
    if analysis.get("is_healthy"):
        return f"Plante : {analysis['plant']}, saine."
    return f"Plante : {analysis['plant']}, maladie : {analysis['disease']}."


def generate_reply(
    session_id: str, message: str, analysis: dict, history: list[dict], location: dict | None = None
) -> str:
    """Génère la réponse du chatbot.

    Args:
        session_id: identifiant de la conversation, utilisé par la mémoire de n8n.
        message: la question de l'utilisateur.
        analysis: le résultat de /api/analyze (champ "result").
        history: les messages précédents, [{"role": "user" | "assistant", "content": "..."}].
        location: la commune de l'utilisateur (facultatif), {"city", "department", "lat", "lon"}.

    Returns:
        Le texte de la réponse.
    """
    payload = {
            "session_id": session_id,
            "message": message,
            "context": build_context(analysis),
            "analysis": {k: analysis.get(k) for k in ("recognized", "label", "plant", "disease", "is_healthy", "confidence")},
            }
    # L'historique n'est envoyé que s'il y a des messages précédents
    if history:
        payload["history"] = history[-10:]
    # La commune n'est envoyée que si l'utilisateur l'a choisie (utile pour l'outil météo)
    if location:
        payload["location"] = location
    """response = requests.post(
        N8N_WEBHOOK_URL,
            json=payload,
            headers={"X-API-Key": N8N_API_KEY},
            timeout=60,
        )
    return response.json()["reply"]
    """
    return json.dumps(payload, ensure_ascii=False, indent=2)

