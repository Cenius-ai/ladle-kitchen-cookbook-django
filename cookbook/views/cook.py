"""Cook-along page: one step at a time, paged by tap, key or voice."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from cookbook.services.access import get_visible_recipe_or_404


@login_required
def cook(request, pk):
    recipe = get_visible_recipe_or_404(request.user, pk)
    return render(
        request,
        "recipes/cook.html",
        {
            "recipe": recipe,
            "steps": recipe.steps or [],
            "step_count": len(recipe.steps or []),
            "is_owner": recipe.owner_id == request.user.id,
        },
    )
