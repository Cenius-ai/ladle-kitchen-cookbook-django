"""Context for the command palette: every jump target on this page's shell."""

import json

from django.urls import reverse

from cookbook.services.access import visible_collections, visible_recipes

RECIPE_LIMIT = 40
COLLECTION_LIMIT = 12


def palette(request):
    """Build the palette index for the current cook (empty when signed out)."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"palette_json": "[]"}

    items = [
        {"label": "Recipe library", "hint": "Page", "url": reverse("recipes:library")},
        {"label": "Import a recipe", "hint": "Action", "url": reverse("recipes:import")},
        {"label": "New recipe", "hint": "Action", "url": reverse("recipes:create")},
        {"label": "Collections", "hint": "Page", "url": reverse("collections:list")},
        {"label": "Join a collection", "hint": "Action", "url": reverse("join")},
    ]

    for recipe in visible_recipes(user)[:RECIPE_LIMIT]:
        items.append(
            {
                "label": recipe.title,
                "hint": "Recipe",
                "url": reverse("recipes:detail", args=[recipe.pk]),
            }
        )

    for collection in visible_collections(user)[:COLLECTION_LIMIT]:
        items.append(
            {
                "label": collection.name,
                "hint": "Collection",
                "url": reverse("collections:detail", args=[collection.pk]),
            }
        )

    return {"palette_json": json.dumps(items)}
