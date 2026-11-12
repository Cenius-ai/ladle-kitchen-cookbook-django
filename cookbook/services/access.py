"""Shared access rules: who may see which recipe or collection.

Every read path goes through these helpers so a cook only reaches recipes they
own or that sit in a collection they belong to, and a foreign id behaves
exactly like a missing one.
"""

from django.db.models import Q
from django.shortcuts import get_object_or_404

from cookbook.models import Collection, Recipe


def visible_recipes(user):
    """Recipes the cook owns plus recipes in collections they belong to."""
    if not user.is_authenticated:
        return Recipe.objects.none()
    return (
        Recipe.objects.filter(
            Q(owner=user) | Q(collection_entries__collection__members__user=user)
        )
        .select_related("owner")
        .distinct()
    )


def owned_recipes(user):
    if not user.is_authenticated:
        return Recipe.objects.none()
    return Recipe.objects.filter(owner=user)


def get_visible_recipe_or_404(user, pk):
    return get_object_or_404(visible_recipes(user), pk=pk)


def get_owned_recipe_or_404(user, pk):
    return get_object_or_404(owned_recipes(user), pk=pk)


def visible_collections(user):
    """Collections the cook owns or has joined."""
    if not user.is_authenticated:
        return Collection.objects.none()
    return (
        Collection.objects.filter(Q(owner=user) | Q(members__user=user))
        .select_related("owner")
        .distinct()
    )


def get_visible_collection_or_404(user, pk):
    return get_object_or_404(visible_collections(user), pk=pk)
