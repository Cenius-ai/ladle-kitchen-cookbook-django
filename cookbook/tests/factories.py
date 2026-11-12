"""Small helpers for the test suite."""

from django.contrib.auth import get_user_model

from cookbook.models import Collection, CollectionMember, Ingredient, Recipe


def make_user(username="cook", password="***REDACTED-SECRET***", **kwargs):
    return get_user_model().objects.create_user(
        username=username, password=password, email=kwargs.pop("email", f"{username}@example.com"), **kwargs
    )


def make_recipe(owner, title="Test loaf", ingredients=("flour", "water"), **kwargs):
    recipe = Recipe.objects.create(
        owner=owner,
        title=title,
        description=kwargs.pop("description", "A test recipe."),
        servings=kwargs.pop("servings", 4),
        steps=kwargs.pop("steps", ["Mix.", "Bake."]),
        nutrition=kwargs.pop("nutrition", {"calories": 320, "protein_g": 12, "carbs_g": 40, "fat_g": 9}),
        origin=kwargs.pop("origin", Recipe.ORIGIN_MANUAL),
        **kwargs,
    )
    Ingredient.objects.bulk_create(
        [Ingredient(recipe=recipe, position=index, text=text) for index, text in enumerate(ingredients)]
    )
    return recipe


def make_collection(owner, name="Weeknight Suppers", invite_code="TESTCODE01", members=()):
    collection = Collection.objects.create(owner=owner, name=name, invite_code=invite_code)
    CollectionMember.objects.create(
        collection=collection, user=owner, role=CollectionMember.ROLE_OWNER
    )
    for member in members:
        CollectionMember.objects.create(
            collection=collection, user=member, role=CollectionMember.ROLE_MEMBER
        )
    return collection
