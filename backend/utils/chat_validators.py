"""Validation des requêtes reçues par le chatbot."""

import re

ROLES = {"user", "assistant"}
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,64}$")  # ex. un UUID


class ChatValidationError(ValueError):
    """Levée quand la requête du chatbot est incomplète ou mal formée."""


def validate_chat_request(
    data, max_message_length: int, max_history: int
) -> tuple[str, str, dict, list[dict]]:
    """Vérifie le corps JSON de /api/chat et renvoie (session_id, message, analysis, history).

    Format attendu :
    {
        "session_id": "a3f9c2e1-7b4d-4e8a-9c1f-2d5e6f7a8b9c",
        "message": "Comment traiter le mildiou ?",
        "analysis": { ... champ "result" renvoyé par /api/analyze ... },
        "history": [{"role": "user" | "assistant", "content": "..."}]   (facultatif)
    }
    """
    if not isinstance(data, dict):
        raise ChatValidationError("Corps JSON attendu.")

    session_id = data.get("session_id")
    if not isinstance(session_id, str) or not SESSION_ID_PATTERN.match(session_id):
        raise ChatValidationError("Le champ 'session_id' est obligatoire (lettres, chiffres et tirets, 64 max).")

    message = data.get("message")
    if not isinstance(message, str) or not message.strip():
        raise ChatValidationError("Le champ 'message' est obligatoire.")
    if len(message) > max_message_length:
        raise ChatValidationError(f"Message trop long (max {max_message_length} caractères).")

    analysis = data.get("analysis")
    if not isinstance(analysis, dict) or not analysis:
        raise ChatValidationError("Le champ 'analysis' (résultat de /api/analyze) est obligatoire.")

    history = data.get("history", [])
    if not isinstance(history, list):
        raise ChatValidationError("Le champ 'history' doit être une liste.")
    if len(history) > max_history:
        raise ChatValidationError(f"Historique trop long (max {max_history} messages).")
    for item in history:
        if (
            not isinstance(item, dict)
            or item.get("role") not in ROLES
            or not isinstance(item.get("content"), str)
        ):
            raise ChatValidationError("Chaque message de 'history' doit avoir un 'role' (user/assistant) et un 'content'.")

    history = [{"role": m["role"], "content": m["content"]} for m in history]
    return session_id, message.strip(), analysis, history

