"""Paste-to-import of schema.org Recipe JSON-LD."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render

from cookbook.models import Ingredient, Recipe
from cookbook.services.jsonld import JsonLdError, parse_recipe

EXAMPLE_JSONLD = """{
  "@context": "https://schema.org",
  "@type": "Recipe",
  "name": "Lemon-garlic roast chicken",
  "recipeYield": "4 servings",
  "recipeIngredient": ["1 whole chicken", "2 lemons", "4 garlic cloves"],
  "recipeInstructions": [
    {"@type": "HowToStep", "text": "Heat the oven to 200C."},
    {"@type": "HowToStep", "text": "Roast for 55 minutes."}
  ],
  "nutrition": {"@type": "NutritionInformation", "calories": "620 kcal"}
}"""


def save_parsed_recipe(owner, parsed):
    """Persist a parsed JSON-LD recipe with its ingredients and steps."""
    with transaction.atomic():
        recipe = Recipe.objects.create(
            owner=owner,
            title=parsed.title,
            description=parsed.description,
            source_url=parsed.source_url,
            image_url=parsed.image_url,
            servings=parsed.servings,
            steps=parsed.steps,
            nutrition=parsed.nutrition,
            origin=Recipe.ORIGIN_IMPORTED,
        )
        Ingredient.objects.bulk_create(
            [
                Ingredient(recipe=recipe, position=index, text=text)
                for index, text in enumerate(parsed.ingredients)
            ]
        )
    return recipe


@login_required
def import_recipe(request):
    raw = ""
    parsed = None
    error = ""

    if request.method == "POST":
        raw = request.POST.get("jsonld", "")
        action = request.POST.get("action", "parse")
        try:
            # The paste is re-parsed on save, so the URL never carries the
            # recipe body as hidden form state.
            parsed = parse_recipe(raw)
        except JsonLdError as exc:
            error = str(exc)
        else:
            if action == "save":
                recipe = save_parsed_recipe(request.user, parsed)
                messages.success(
                    request, f"Imported “{recipe.title}” with {recipe.ingredients.count()} ingredients."
                )
                return redirect("recipes:detail", pk=recipe.pk)

    return render(
        request,
        "recipes/import.html",
        {
            "raw": raw,
            "parsed": parsed if not error else None,
            "error": error,
            "example": EXAMPLE_JSONLD,
        },
    )
