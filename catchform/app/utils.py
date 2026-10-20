"""Petites fonctions partagées."""
import json


def as_text(value):
    """Représentation texte d'une valeur de champ (form-data ou JSON)."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)
