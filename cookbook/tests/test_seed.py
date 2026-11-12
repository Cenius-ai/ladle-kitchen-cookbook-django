"""The seed command is idempotent and leaves a demo household that renders."""

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from cookbook.models import Collection, Recipe


class SeedCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", quiet=True)

    def test_seeds_six_recipes_and_two_collections(self):
        self.assertEqual(Recipe.objects.count(), 6)
        self.assertEqual(Collection.objects.count(), 2)
        self.assertEqual(get_user_model().objects.count(), 2)

    def test_the_standard_demo_login_works_and_reaches_the_library(self):
        user = get_user_model().objects.get(username="cenius")
        self.assertEqual(user.email, "cenius@cenius.ai")
        self.assertTrue(user.check_password("cenius"))

        response = self.client.post(
            reverse("auth:login"), {"identifier": "cenius@cenius.ai", "password": "cenius"}
        )
        self.assertRedirects(response, reverse("recipes:library"))
        library = self.client.get(reverse("recipes:library"))
        self.assertEqual(library.status_code, 200)
        for recipe in Recipe.objects.all():
            self.assertContains(library, recipe.title)

    def test_seeded_recipes_carry_ingredients_steps_and_nutrition(self):
        with_lines = Recipe.objects.filter(origin=Recipe.ORIGIN_IMPORTED).exclude(nutrition={})
        self.assertGreaterEqual(with_lines.count(), 5)
        for recipe in with_lines:
            self.assertGreater(recipe.ingredients.count(), 0)
            self.assertGreater(len(recipe.steps), 0)
            self.assertIsNotNone(recipe.nutrition.get("calories"))

    def test_one_seeded_recipe_has_no_nutrition_so_the_override_panel_shows(self):
        empty = [recipe for recipe in Recipe.objects.all() if not recipe.nutrition]
        self.assertEqual(len(empty), 1)

    def test_second_run_adds_nothing(self):
        call_command("seed_demo", quiet=True)
        call_command("seed_demo", quiet=True)
        self.assertEqual(Recipe.objects.count(), 6)
        self.assertEqual(Collection.objects.count(), 2)
        self.assertEqual(get_user_model().objects.count(), 2)

    def test_the_second_cook_shares_a_collection_with_the_demo_cook(self):
        cenius = get_user_model().objects.get(username="cenius")
        marta = get_user_model().objects.get(username="marta")
        weeknight = Collection.objects.get(name="Weeknight Suppers")
        self.assertEqual(weeknight.owner, cenius)
        self.assertTrue(weeknight.is_member(marta))

        baking = Collection.objects.get(name="Weekend Baking")
        self.assertEqual(baking.owner, marta)
        self.assertTrue(baking.is_member(cenius))

    def test_seeded_recipe_pages_render_for_the_demo_cook(self):
        self.client.login(username="cenius", password="cenius")
        for recipe in Recipe.objects.all():
            response = self.client.get(reverse("recipes:detail", args=[recipe.pk]))
            self.assertEqual(response.status_code, 200, recipe.title)
