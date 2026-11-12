"""Paste-to-import: preview, save and clear errors."""

import json

from django.test import TestCase
from django.urls import reverse

from cookbook.models import Recipe
from cookbook.tests.factories import make_user

JSONLD = {
    "@context": "https://schema.org",
    "@type": "Recipe",
    "name": "Imported lemon cake",
    "recipeYield": "8 servings",
    "recipeIngredient": ["200 g butter", "200 g sugar", "3 lemons"],
    "recipeInstructions": [
        {"@type": "HowToStep", "text": "Cream the butter and sugar."},
        {"@type": "HowToStep", "text": "Fold in the flour and bake."},
    ],
    "nutrition": {"calories": "340 kcal", "proteinContent": "4 g", "carbohydrateContent": "46 g", "fatContent": "16 g"},
}
PASTE = f'<script type="application/ld+json">{json.dumps(JSONLD)}</script>'


class ImportScreenTests(TestCase):
    def setUp(self):
        self.owner = make_user(username="owner")
        self.client.force_login(self.owner)

    def test_parse_shows_a_preview_without_saving(self):
        response = self.client.post(reverse("recipes:import"), {"jsonld": PASTE, "action": "parse"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Imported lemon cake")
        self.assertContains(response, "8 servings")
        self.assertContains(response, "340")
        self.assertContains(response, "Save recipe")
        self.assertEqual(Recipe.objects.count(), 0)

    def test_save_persists_the_imported_recipe(self):
        response = self.client.post(reverse("recipes:import"), {"jsonld": PASTE, "action": "save"})
        recipe = Recipe.objects.get(title="Imported lemon cake")
        self.assertRedirects(response, reverse("recipes:detail", args=[recipe.pk]))
        self.assertEqual(recipe.origin, Recipe.ORIGIN_IMPORTED)
        self.assertEqual(recipe.servings, 8)
        self.assertEqual(recipe.ingredients.count(), 3)
        self.assertEqual(len(recipe.steps), 2)
        self.assertEqual(recipe.nutrition["calories"], 340)

        detail = self.client.get(reverse("recipes:detail", args=[recipe.pk]))
        self.assertContains(detail, "Imported figures")
        self.assertContains(detail, "2,720")  # 340 x 8

        library = self.client.get(reverse("recipes:library"))
        self.assertContains(library, "Imported lemon cake")

    def test_html_without_json_ld_shows_a_banner_and_keeps_the_paste(self):
        paste = "<html><body><h1>Ordinary page</h1></body></html>"
        response = self.client.post(reverse("recipes:import"), {"jsonld": paste, "action": "parse"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "That paste did not parse")
        self.assertContains(response, "No Recipe JSON-LD was found")
        self.assertContains(response, "Ordinary page")
        self.assertEqual(Recipe.objects.count(), 0)

    def test_missing_ingredients_names_the_field(self):
        paste = json.dumps({"@type": "Recipe", "name": "Mystery soup"})
        response = self.client.post(reverse("recipes:import"), {"jsonld": paste, "action": "parse"})
        self.assertContains(response, "recipeIngredient")
        self.assertEqual(Recipe.objects.count(), 0)

    def test_malformed_json_does_not_raise_a_traceback(self):
        response = self.client.post(reverse("recipes:import"), {"jsonld": "{not json", "action": "parse"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Could not read that JSON")
