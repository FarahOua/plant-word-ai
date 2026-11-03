"""Route d'analyse d'image."""

from flask import Blueprint, current_app, jsonify, request

from services.analyzer import analyze_image
from services.classifier import ModelUnavailableError
from utils.validators import ImageValidationError, validate_image

analyze_bp = Blueprint("analyze", __name__)


@analyze_bp.post("/analyze")
def analyze():
    """Reçoit une image (champ multipart `image`) et renvoie le résultat de l'analyse."""
    file = request.files.get("image")

    try:
        image = validate_image(
            file,
            allowed_extensions=current_app.config["ALLOWED_EXTENSIONS"],
            allowed_formats=current_app.config["ALLOWED_IMAGE_FORMATS"],
        )
    except ImageValidationError as error:
        return jsonify({"success": False, "error": str(error)}), 400

    try:
        result = analyze_image(image)
    except ModelUnavailableError as error:
        current_app.logger.error(error)
        return jsonify({"success": False, "error": "Le modèle d'analyse est indisponible pour le moment."}), 503

    return jsonify({
        "success": True,
        "filename": file.filename,
        "image": {"format": image.format, "width": image.width, "height": image.height},
        "result": result,
    }), 200
