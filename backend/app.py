import os

from flask import Flask, jsonify
from werkzeug.exceptions import RequestEntityTooLarge

from config import Config
from routes.analyze import analyze_bp
from routes.chat import chat_bp
from routes.evaluation import evaluation_bp
from services.classifier import ModelUnavailableError, get_classifier


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    app.register_blueprint(analyze_bp, url_prefix="/api")
    app.register_blueprint(chat_bp, url_prefix="/api")
    app.register_blueprint(evaluation_bp, url_prefix="/api")

    # Charge le modèle dès le démarrage pour que la première analyse soit rapide.
    # En cas d'échec, l'API démarre quand même et /api/analyze renverra une erreur 503.
    # En mode debug, Flask lance un processus de surveillance + un processus serveur :
    # on ne charge le modèle que dans le processus serveur (WERKZEUG_RUN_MAIN).
    is_reloader_parent = app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true"
    if app.config["MODEL_PRELOAD"] and not is_reloader_parent:
        try:
            get_classifier()
            app.logger.info("Modèle chargé : %s", app.config["MODEL_NAME"])
        except ModelUnavailableError as error:
            app.logger.error(error)

    @app.errorhandler(RequestEntityTooLarge)
    def file_too_large(_error):
        max_mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        return jsonify({"success": False, "error": f"Fichier trop volumineux (max {max_mb} Mo)."}), 413

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"success": False, "error": "Ressource introuvable."}), 404

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return jsonify({"success": False, "error": "Méthode non autorisée."}), 405

    @app.errorhandler(500)
    def internal_error(_error):
        return jsonify({"success": False, "error": "Erreur interne du serveur."}), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
