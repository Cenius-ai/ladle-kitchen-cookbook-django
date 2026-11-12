"""Template filters and tags used by the Ladle templates."""

from django import template
from django.templatetags.static import static

register = template.Library()

COVER_COUNT = 6


@register.filter
def number(value):
    """Render a nutrient figure with thousands separators, or an em dash."""
    if value is None or value == "":
        return "—"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "—"
    if numeric.is_integer():
        return f"{numeric:,.0f}"
    return f"{numeric:,.1f}"


@register.filter
def initials(user):
    """Two-letter avatar text for a username."""
    text = getattr(user, "username", "") or str(user)
    parts = [part for part in text.replace("_", "-").split("-") if part]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][:1] + parts[1][:1]).upper()


@register.filter
def get_item(mapping, key):
    """Look up a dict value with a variable key (Django cannot do dict[key])."""
    if hasattr(mapping, "get"):
        return mapping.get(key)
    return None


@register.simple_tag
def cover_art(recipe):
    """Deterministic local cover art, so no page depends on a remote image."""
    index = (getattr(recipe, "pk", 0) or 0) % COVER_COUNT + 1
    return static(f"img/covers/cover-{index}.svg")
