"""Validation des fichiers image reçus par l'API."""

from PIL import Image, UnidentifiedImageError
from werkzeug.datastructures import FileStorage


class ImageValidationError(ValueError):
    """Levée quand le fichier reçu n'est pas une image valide."""


def _extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def validate_image(file: FileStorage | None, allowed_extensions: set[str], allowed_formats: set[str]) -> Image.Image:
    """Vérifie le fichier et renvoie l'image ouverte avec Pillow.

    Contrôles effectués :
    - un fichier est présent et non vide ;
    - l'extension est autorisée ;
    - le contenu est réellement une image d'un format autorisé (pas seulement l'extension).
    """
    if file is None or not file.filename:
        raise ImageValidationError("Aucun fichier reçu (champ 'image' attendu).")

    if _extension(file.filename) not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise ImageValidationError(f"Extension non autorisée. Formats acceptés : {allowed}.")

    try:
        # verify() détecte les fichiers corrompus mais rend l'objet inutilisable,
        # on rouvre donc l'image ensuite.
        Image.open(file.stream).verify()
        file.stream.seek(0)
        image = Image.open(file.stream)
        image.load()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ImageValidationError("Le fichier n'est pas une image valide ou est corrompu.")

    if image.format not in allowed_formats:
        raise ImageValidationError(f"Format d'image non supporté : {image.format}.")

    return image
