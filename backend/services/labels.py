"""Traduction des 38 classes PlantVillage en informations lisibles (français).

Clé : nom de classe renvoyé par le modèle (format PlantVillage « Plante___Etat »).
Valeur : (nom de la plante, nom de la maladie ou None si la plante est saine).
"""

PLANTVILLAGE_LABELS: dict[str, tuple[str, str | None]] = {
    "Apple___Apple_scab": ("Pommier", "Tavelure"),
    "Apple___Black_rot": ("Pommier", "Pourriture noire"),
    "Apple___Cedar_apple_rust": ("Pommier", "Rouille du pommier"),
    "Apple___healthy": ("Pommier", None),
    "Blueberry___healthy": ("Myrtillier", None),
    "Cherry_(including_sour)___Powdery_mildew": ("Cerisier", "Oïdium"),
    "Cherry_(including_sour)___healthy": ("Cerisier", None),
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": ("Maïs", "Cercosporiose (taches grises)"),
    "Corn_(maize)___Common_rust_": ("Maïs", "Rouille commune"),
    "Corn_(maize)___Northern_Leaf_Blight": ("Maïs", "Helminthosporiose"),
    "Corn_(maize)___healthy": ("Maïs", None),
    "Grape___Black_rot": ("Vigne", "Black-rot"),
    "Grape___Esca_(Black_Measles)": ("Vigne", "Esca"),
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": ("Vigne", "Taches foliaires (Isariopsis)"),
    "Grape___healthy": ("Vigne", None),
    "Orange___Haunglongbing_(Citrus_greening)": ("Oranger", "Huanglongbing (verdissement des agrumes)"),
    "Peach___Bacterial_spot": ("Pêcher", "Tache bactérienne"),
    "Peach___healthy": ("Pêcher", None),
    "Pepper,_bell___Bacterial_spot": ("Poivron", "Tache bactérienne"),
    "Pepper,_bell___healthy": ("Poivron", None),
    "Potato___Early_blight": ("Pomme de terre", "Alternariose"),
    "Potato___Late_blight": ("Pomme de terre", "Mildiou"),
    "Potato___healthy": ("Pomme de terre", None),
    "Raspberry___healthy": ("Framboisier", None),
    "Soybean___healthy": ("Soja", None),
    "Squash___Powdery_mildew": ("Courge", "Oïdium"),
    "Strawberry___Leaf_scorch": ("Fraisier", "Brûlure des feuilles"),
    "Strawberry___healthy": ("Fraisier", None),
    "Tomato___Bacterial_spot": ("Tomate", "Tache bactérienne"),
    "Tomato___Early_blight": ("Tomate", "Alternariose"),
    "Tomato___Late_blight": ("Tomate", "Mildiou"),
    "Tomato___Leaf_Mold": ("Tomate", "Cladosporiose"),
    "Tomato___Septoria_leaf_spot": ("Tomate", "Septoriose"),
    "Tomato___Spider_mites Two-spotted_spider_mite": ("Tomate", "Acariens (tétranyque tisserand)"),
    "Tomato___Target_Spot": ("Tomate", "Corynesporiose (tache cible)"),
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": ("Tomate", "Virus des feuilles jaunes en cuillère (TYLCV)"),
    "Tomato___Tomato_mosaic_virus": ("Tomate", "Virus de la mosaïque de la tomate (ToMV)"),
    "Tomato___healthy": ("Tomate", None),
}


def _clean(text: str) -> str:
    return " ".join(text.replace("_", " ").split())


def describe_label(label: str) -> tuple[str, str | None]:
    """Renvoie (plante, maladie). Pour une classe inconnue, devine à partir du nom brut.

    Le repli est approximatif (noms en anglais, plante sur plusieurs mots mal découpée) :
    pour un nouveau modèle, ajoutez ses classes au dictionnaire ci-dessus.
    """
    if label in PLANTVILLAGE_LABELS:
        return PLANTVILLAGE_LABELS[label]

    # Format PlantVillage « Plante___Etat »
    if "___" in label:
        plant, _, state = label.partition("___")
    # Autres formats, ex. « Wheat_Stripe_Rust » : premier mot = plante, le reste = état
    else:
        plant, _, state = label.strip("_").partition("_")

    plant, state = _clean(plant), _clean(state)
    if "healthy" in state.lower() or not state and "healthy" in plant.lower():
        return plant.replace("healthy", "").strip() or plant, None
    # Sans état identifiable, on ne déclare surtout pas la plante saine
    return plant, state or "inconnue"
