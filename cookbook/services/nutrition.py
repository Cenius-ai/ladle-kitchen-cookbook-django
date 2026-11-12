"""Nutrition maths for per-portion and batch figures.

Values travel as plain dicts keyed by :data:`NUTRIENT_FIELDS` so this module
never touches the ORM: a view hands in the imported blob, the manual override
blob and the serving count, and gets numbers back.
"""

import re

NUTRIENT_FIELDS = ("calories", "protein_g", "carbs_g", "fat_g")

NUTRIENT_LABELS = {
    "calories": "Calories",
    "protein_g": "Protein",
    "carbs_g": "Carbs",
    "fat_g": "Fat",
}

NUTRIENT_UNITS = {
    "calories": "kcal",
    "protein_g": "g",
    "carbs_g": "g",
    "fat_g": "g",
}

# Schema.org NutritionInformation property names, in the order we map them.
SCHEMA_ORG_PROPERTIES = {
    "calories": "calories",
    "protein_g": "proteinContent",
    "carbs_g": "carbohydrateContent",
    "fat_g": "fatContent",
}

_NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")


def to_number(value):
    """Return a float from a JSON-LD nutrient value, or None when unusable."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = _NUMBER_RE.search(str(value))
    if match is None:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


def from_schema_org(node):
    """Map a schema.org NutritionInformation object onto our nutrient keys."""
    if not isinstance(node, dict):
        return {}
    values = {}
    for field, prop in SCHEMA_ORG_PROPERTIES.items():
        number = to_number(node.get(prop))
        if number is not None:
            values[field] = number
    return values


def resolve(imported, override):
    """Per-portion figures: the manual override wins over imported numbers."""
    source = override if has_values(override) else imported
    if not isinstance(source, dict):
        return {field: None for field in NUTRIENT_FIELDS}
    return {field: to_number(source.get(field)) for field in NUTRIENT_FIELDS}


def has_values(values):
    if not isinstance(values, dict):
        return False
    return any(to_number(values.get(field)) is not None for field in NUTRIENT_FIELDS)


def batch(values, servings):
    """Multiply per-portion figures by the serving count."""
    servings = servings if isinstance(servings, int) and servings > 0 else 1
    return {
        field: None if values.get(field) is None else values[field] * servings
        for field in NUTRIENT_FIELDS
    }


def source_label(imported, override):
    """Which badge the detail panel shows: manual, imported or none."""
    if has_values(override):
        return "manual"
    if has_values(imported):
        return "imported"
    return "none"
