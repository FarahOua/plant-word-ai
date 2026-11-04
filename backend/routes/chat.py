"""Route du chatbot : discuter de l'image analysée et de son diagnostic."""

from flask import Blueprint, current_app, jsonify, request

from services.chatbot import ChatbotUnavailableError, generate_reply
from utils.chat_validators import ChatValidationError, validate_chat_request
import json

chat_bp = Blueprint("chat", __name__)


@chat_bp.post("/chat")
def chat():
    """Reçoit une question, le résultat de l'analyse et l'historique, puis renvoie la réponse."""
    try:
        message, analysis, history, location = validate_chat_request(
            request.get_json(silent=True),
            max_message_length=current_app.config["CHAT_MAX_MESSAGE_LENGTH"],
            max_history=current_app.config["CHAT_MAX_HISTORY"],
        )
    except ChatValidationError as error:
        return jsonify({"success": False, "error": str(error)}), 400

    try:
        reply = generate_reply(message, analysis, history, location)
    except ChatbotUnavailableError as error:
        current_app.logger.error(error)
        return jsonify({"success": False, "error": "Le chatbot est indisponible pour le moment."}), 503

    return jsonify({"success": True, "reply": reply}), 200
