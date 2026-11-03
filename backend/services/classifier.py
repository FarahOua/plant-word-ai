"""Classification des maladies de plantes avec un modèle Hugging Face pré-entraîné.

Fonctionne avec n'importe quel modèle de classification d'images Hugging Face
(MobileNetV2, ViT, ResNet, EfficientNet...) : l'architecture est détectée
automatiquement à partir du config.json du modèle (classes « Auto »).

Le modèle est téléchargé au premier lancement, puis réutilisé depuis le cache
local. Il est chargé une seule fois et partagé entre toutes les requêtes.
"""

import threading
from dataclasses import dataclass

import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForImageClassification

try:  # Transformers 5 : préprocesseur basé sur Pillow (sans torchvision)
    from transformers import MobileNetV2ImageProcessorPil as MobileNetV2ImageProcessor
except ImportError:  # Versions plus anciennes
    from transformers import MobileNetV2ImageProcessor

from config import Config


class ModelUnavailableError(RuntimeError):
    """Le modèle n'a pas pu être chargé (pas d'internet au 1er lancement, nom invalide...)."""


@dataclass
class Prediction:
    label: str          # nom brut de la classe, ex. "Tomato___Late_blight"
    confidence: float   # probabilité entre 0 et 1


class PlantClassifier:
    def __init__(self, model_name: str, revision: str | None = None, device: str = "cpu"):
        self.model_name = model_name
        self.device = torch.device(device)
        try:
            # Le réseau : l'architecture est lue dans config.json ("model_type")
            self.model = AutoModelForImageClassification.from_pretrained(model_name, revision=revision)
            # Le prétraitement : les règles utilisées pendant l'entraînement
            self.processor = self._load_processor(model_name, revision)
        except Exception as error:
            raise ModelUnavailableError(f"Impossible de charger le modèle '{model_name}' : {error}") from error

        self.model.to(self.device).eval()

    def _load_processor(self, model_name: str, revision: str | None):
        try:
            return AutoImageProcessor.from_pretrained(model_name, revision=revision)
        except ValueError:
            # Certains anciens modèles MobileNetV2 déclarent un nom de préprocesseur
            # ("MobileNetV2FeatureExtractor") que Transformers 5 ne reconnaît plus.
            # Le repli n'est sûr que pour MobileNetV2 : pour une autre architecture,
            # on préfère une erreur claire à un prétraitement incorrect.
            if self.model.config.model_type != "mobilenet_v2":
                raise
            return MobileNetV2ImageProcessor.from_pretrained(model_name, revision=revision)

    def predict(self, image: Image.Image, top_k: int = 3) -> list[Prediction]:
        """Renvoie les `top_k` classes les plus probables, de la plus probable à la moins probable."""
        # Même prétraitement qu'à l'entraînement : redimensionnement, recadrage 224x224, normalisation
        inputs = self.processor(images=image.convert("RGB"), return_tensors="pt").to(self.device)

        with torch.inference_mode():
            probabilities = self.model(**inputs).logits.softmax(dim=-1)[0]

        scores, indices = probabilities.topk(min(top_k, probabilities.numel()))
        return [
            Prediction(label=self.model.config.id2label[int(index)], confidence=float(score))
            for score, index in zip(scores, indices)
        ]


_classifier: PlantClassifier | None = None
_lock = threading.Lock()


def get_classifier() -> PlantClassifier:
    """Renvoie l'instance unique du classifieur, en la chargeant au premier appel."""
    global _classifier
    if _classifier is None:
        with _lock:
            if _classifier is None:
                _classifier = PlantClassifier(Config.MODEL_NAME, Config.MODEL_REVISION, Config.MODEL_DEVICE)
    return _classifier
