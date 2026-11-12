"""Recipe library, detail page and manual create / edit / delete."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import redirect, render
from django.urls import reverse

from cookbook.forms import NutritionOverrideForm, RecipeForm
from cookbook.models import Recipe
from cookbook.services import nutrition as nutrition_service
from cookbook.services.access import (
    get_owned_recipe_or_404,
    get_visible_recipe_or_404,
    visible_collections,
    visible_recipes,
)

RECENT_LIMIT = 3


@login_required
def library(request):
    query = (request.GET.get("q") or "").strip()
    collection_param = (request.GET.get("collection") or "").strip()

    recipes = visible_recipes(request.user)
    collections = visible_collections(request.user).annotate(
        recipe_total=Count("recipe_entries", distinct=True)
    )

    selected_collection = None
    if collection_param.isdigit():
        selected_collection = collections.filter(pk=int(collection_param)).first()
        if selected_collection is not None:
            recipes = recipes.filter(collection_entries__collection=selected_collection)
        else:
            # A collection that does not exist (or is not ours) simply does not filter.
            recipes = recipes.none()

    if query:
        recipes = recipes.filter(title__icontains=query)

    recipe_rows = list(recipes.distinct().order_by("title"))
    recent = list(
        visible_recipes(request.user).order_by("-updated_at")[:RECENT_LIMIT]
    )

    return render(
        request,
        "recipes/list.html",
        {
            "recipes": recipe_rows,
            "collections": collections,
            "recent": recent,
            "query": query,
            "selected_collection": selected_collection,
            "total_recipes": visible_recipes(request.user).count(),
            "has_filters": bool(query or selected_collection),
        },
    )


def render_detail(request, recipe, override_form=None, status=200):
    """Render the recipe detail page, optionally with an override form in error."""
    collections = visible_collections(request.user).annotate(
        recipe_total=Count("recipe_entries", distinct=True)
    )
    joined_ids = set(recipe.collection_entries.values_list("collection_id", flat=True))
    collection_options = [
        {"collection": collection, "contains": collection.id in joined_ids}
        for collection in collections
    ]
    per_portion = recipe.per_portion_nutrition()
    return render(
        request,
        "recipes/detail.html",
        {
            "recipe": recipe,
            "ingredients": recipe.ingredients.all(),
            "per_portion": per_portion,
            "batch": nutrition_service.batch(per_portion, recipe.servings),
            "nutrition_source": recipe.nutrition_source(),
            "nutrition_labels": nutrition_service.NUTRIENT_LABELS,
            "nutrition_units": nutrition_service.NUTRIENT_UNITS,
            "nutrition_fields": nutrition_service.NUTRIENT_FIELDS,
            "override_form": override_form
            or NutritionOverrideForm(
                initial={
                    field: (recipe.nutrition_override or {}).get(field)
                    for field in nutrition_service.NUTRIENT_FIELDS
                }
            ),
            "collection_options": collection_options,
            "is_owner": recipe.owner_id == request.user.id,
            "cook_url": reverse("recipes:cook", args=[recipe.pk]),
        },
        status=status,
    )


@login_required
def detail(request, pk):
    recipe = get_visible_recipe_or_404(request.user, pk)
    return render_detail(request, recipe)


@login_required
def create(request):
    form = RecipeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        recipe = form.save(commit=False)
        recipe.owner = request.user
        recipe.origin = Recipe.ORIGIN_MANUAL
        recipe.save()
        form.save_ingredients(recipe)
        messages.success(request, f"“{recipe.title}” was added to your cookbook.")
        return redirect("recipes:detail", pk=recipe.pk)

    return render(
        request,
        "recipes/form.html",
        {"form": form, "mode": "create", "recipe": None},
    )


@login_required
def edit(request, pk):
    recipe = get_owned_recipe_or_404(request.user, pk)
    form = RecipeForm(request.POST or None, instance=recipe)
    if request.method == "POST" and form.is_valid():
        recipe = form.save()
        messages.success(request, f"“{recipe.title}” was saved.")
        return redirect("recipes:detail", pk=recipe.pk)

    return render(
        request,
        "recipes/form.html",
        {"form": form, "mode": "edit", "recipe": recipe},
    )


@login_required
def delete(request, pk):
    recipe = get_owned_recipe_or_404(request.user, pk)
    if request.method == "POST":
        title = recipe.title
        recipe.delete()
        messages.success(request, f"“{title}” was deleted.")
        return redirect("recipes:library")

    return render(request, "recipes/confirm_delete.html", {"recipe": recipe})
