"""Manual nutrition overrides on the recipe detail page."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from cookbook.forms import NutritionOverrideForm
from cookbook.services.access import get_owned_recipe_or_404
from cookbook.views.recipes import render_detail


@login_required
@require_POST
def set_override(request, pk):
    recipe = get_owned_recipe_or_404(request.user, pk)
    form = NutritionOverrideForm(request.POST)
    if form.is_valid():
        recipe.nutrition_override = {
            field: round(value, 2) for field, value in form.values.items()
        }
        recipe.save(update_fields=["nutrition_override", "updated_at"])
        messages.success(request, "Manual nutrition saved for this recipe.")
        return redirect("recipes:detail", pk=recipe.pk)

    messages.error(request, "Check the four nutrition figures and try again.")
    return render_detail(request, recipe, override_form=form)


@login_required
@require_POST
def clear_override(request, pk):
    recipe = get_owned_recipe_or_404(request.user, pk)
    recipe.nutrition_override = {}
    recipe.save(update_fields=["nutrition_override", "updated_at"])
    messages.success(request, "Manual override cleared — imported figures restored.")
    return redirect("recipes:detail", pk=recipe.pk)
