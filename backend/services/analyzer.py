"""Logique d'analyse d'image.

Étape actuelle : détection de la plante et de sa maladie avec le classifieur.
Étape suivante possible : enrichir le résultat avec le RAG (n8n) à partir
de la plante et de la maladie détectées.
"""

from PIL import Image

from config import Config
from services.classifier import get_classifier
from services.labels import describe_label


def analyze_image(image: Image.Image) -> dict:
    """Analyse une image de feuille et renvoie le diagnostic."""
    classifier = get_classifier()
    best = classifier.predict(image, top_k=1)[0]

    plant, disease = describe_label(best.label)
    recognized = best.confidence >= Config.CONFIDENCE_THRESHOLD

    return {
        "recognized": recognized,
        "plant": plant if recognized else None,
        "disease": disease if recognized else None,
        "is_healthy": (disease is None) if recognized else None,
        "confidence": round(best.confidence, 4),
    }
