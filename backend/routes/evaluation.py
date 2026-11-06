"""Routes de l'évaluation du workflow n8n."""

from flask import Blueprint, jsonify, request

from services.evaluation import EvaluationError, load_suite, run_case, save_feedback

evaluation_bp = Blueprint("evaluation", __name__)


@evaluation_bp.get("/evaluation/cases")
def list_cases():
    """Renvoie les diagnostics de test et la liste des questions."""
    return jsonify({"success": True, **load_suite()}), 200


@evaluation_bp.post("/evaluation/run")
def run():
    """Exécute un cas : appel du workflow, contrôles par règles et juge LLM."""
    try:
        result = run_case((request.get_json(silent=True) or {}).get("case"))
    except EvaluationError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    return jsonify({"success": True, **result}), 200


@evaluation_bp.post("/evaluation/feedback")
def feedback():
    """Enregistre l'avis humain sur une réponse."""
    try:
        save_feedback(request.get_json(silent=True))
    except EvaluationError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    return jsonify({"success": True}), 200
