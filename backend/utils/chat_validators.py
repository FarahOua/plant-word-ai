"""Validation des requêtes reçues par le chatbot."""

ROLES = {"user", "assistant"}


class ChatValidationError(ValueError):
    """Levée quand la requête du chatbot est incomplète ou mal formée."""


def validate_chat_request(data, max_message_length: int, max_history: int) -> tuple[str, dict, list[dict], dict | None]:
    """Vérifie le corps JSON de /api/chat et renvoie (message, analysis, history, location).

    Format attendu :
    {
        "message": "Comment traiter le mildiou ?",
        "analysis": { ... champ "result" renvoyé par /api/analyze ... },
        "history": [{"role": "user" | "assistant", "content": "..."}],   (facultatif)
        "location": {"city": "Lyon", "department": "69", "lat": 45.76, "lon": 4.84}   (facultatif)
    }
    """
    if not isinstance(data, dict):
        raise ChatValidationError("Corps JSON attendu.")

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

    location = _validate_location(data.get("location"))

    history = [{"role": m["role"], "content": m["content"]} for m in history]
    return message.strip(), analysis, history, location


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_location(location) -> dict | None:
    """Vérifie la commune choisie (facultative) et ne garde que les champs attendus."""
    if location is None:
        return None
    if not isinstance(location, dict):
        raise ChatValidationError("Le champ 'location' doit être un objet.")

    city, department = location.get("city"), location.get("department")
    lat, lon = location.get("lat"), location.get("lon")
    if not isinstance(city, str) or not city.strip() or len(city) > 100:
        raise ChatValidationError("'location.city' doit être un nom de commune.")
    if not isinstance(department, str) or not 1 <= len(department) <= 3:
        raise ChatValidationError("'location.department' doit être un code de département (ex. 69, 2A, 974).")
    if not _is_number(lat) or not -90 <= lat <= 90 or not _is_number(lon) or not -180 <= lon <= 180:
        raise ChatValidationError("'location.lat' et 'location.lon' doivent être des coordonnées valides.")

    return {"city": city.strip(), "department": department, "lat": lat, "lon": lon}
