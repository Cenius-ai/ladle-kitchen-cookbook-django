"""Recipe library, isolation between cooks, manual CRUD and nutrition overrides."""

from django.test import TestCase
from django.urls import reverse

from cookbook.models import CollectionRecipe, Recipe
from cookbook.tests.factories import make_collection, make_recipe, make_user


class LibraryTests(TestCase):
    def setUp(self):
        self.owner = make_user(username="owner")
        self.other = make_user(username="stranger")
        self.chicken = make_recipe(self.owner, title="Chicken traybake")
        self.pasta = make_recipe(self.owner, title="Weeknight pasta")
        self.client.force_login(self.owner)

    def test_library_lists_every_owned_recipe(self):
        response = self.client.get(reverse("recipes:library"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chicken traybake")
        self.assertContains(response, "Weeknight pasta")

    def test_search_filters_by_title(self):
        response = self.client.get(reverse("recipes:library"), {"q": "tray"})
        html = response.content.decode()
        self.assertIn("Chicken traybake</a>", html)
        # Only the matching row renders (the palette index still lists every title).
        self.assertEqual(html.count('class="recipe-title"'), 1)

    def test_no_match_quotes_the_search_term(self):
        response = self.client.get(reverse("recipes:library"), {"q": "sourdough"})
        self.assertContains(response, "Nothing matched")
        self.assertContains(response, "sourdough")

    def test_recipes_shared_through_a_collection_are_visible(self):
        household = make_collection(self.owner, name="Household", members=[self.other])
        shared = make_recipe(self.other, title="Marta banana bread")
        CollectionRecipe.objects.create(collection=household, recipe=shared, added_by=self.other)

        response = self.client.get(reverse("recipes:library"))
        self.assertContains(response, "Marta banana bread")

    def test_foreign_recipe_is_a_404(self):
        private = make_recipe(self.other, title="Private stew")
        response = self.client.get(f"/recipes/{private.pk}/")
        self.assertEqual(response.status_code, 404)


class DetailTests(TestCase):
    def setUp(self):
        self.owner = make_user(username="owner")
        self.recipe = make_recipe(self.owner, title="Chicken traybake", ingredients=("1 chicken", "2 lemons"))
        self.client.force_login(self.owner)

    def test_detail_lists_ingredients_and_numbered_steps(self):
        response = self.client.get(reverse("recipes:detail", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1 chicken")
        self.assertContains(response, "Mix.")
        self.assertContains(response, "Method")

    def test_nutrition_panel_shows_per_portion_and_batch(self):
        response = self.client.get(reverse("recipes:detail", args=[self.recipe.pk]))
        self.assertContains(response, "320")
        self.assertContains(response, "1,280")  # 320 x 4 servings
        self.assertContains(response, "Imported figures")

    def test_recipe_without_nutrition_invites_an_override(self):
        bare = make_recipe(self.owner, title="Bare stew", nutrition={})
        response = self.client.get(reverse("recipes:detail", args=[bare.pk]))
        self.assertContains(response, "Add manual override")
        self.assertContains(response, "arrived without nutrition")


class ManualCreateTests(TestCase):
    def setUp(self):
        self.owner = make_user(username="owner")
        self.client.force_login(self.owner)

    def test_create_persists_ingredients_and_steps(self):
        response = self.client.post(
            reverse("recipes:create"),
            {
                "title": "Weeknight pasta",
                "description": "Fifteen minutes flat.",
                "servings": 2,
                "image_url": "",
                "source_url": "",
                "ingredients_text": "200 g pasta\n1 tin tomatoes\n2 cloves garlic",
                "steps_text": "Boil the pasta.\nSimmer the sauce.",
            },
        )
        recipe = Recipe.objects.get(title="Weeknight pasta")
        self.assertRedirects(response, reverse("recipes:detail", args=[recipe.pk]))
        self.assertEqual(recipe.owner, self.owner)
        self.assertEqual(recipe.origin, Recipe.ORIGIN_MANUAL)
        self.assertEqual([line.text for line in recipe.ingredients.all()], ["200 g pasta", "1 tin tomatoes", "2 cloves garlic"])
        self.assertEqual(recipe.steps, ["Boil the pasta.", "Simmer the sauce."])

        detail = self.client.get(reverse("recipes:detail", args=[recipe.pk]))
        self.assertContains(detail, "2 cloves garlic")

    def test_blank_title_re_renders_with_the_typed_values(self):
        response = self.client.post(
            reverse("recipes:create"),
            {
                "title": "   ",
                "description": "",
                "servings": 4,
                "image_url": "",
                "source_url": "",
                "ingredients_text": "200 g pasta",
                "steps_text": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required.")
        self.assertContains(response, "200 g pasta")
        self.assertEqual(Recipe.objects.count(), 0)

    def test_missing_ingredients_is_rejected_at_the_field(self):
        response = self.client.post(
            reverse("recipes:create"),
            {
                "title": "Empty pot",
                "servings": 4,
                "ingredients_text": "",
                "steps_text": "",
            },
        )
        self.assertContains(response, "Add at least one ingredient")
        self.assertEqual(Recipe.objects.count(), 0)

    def test_scheme_less_image_url_is_accepted(self):
        self.client.post(
            reverse("recipes:create"),
            {
                "title": "Photo pasta",
                "servings": 2,
                "image_url": "example.com/pasta.jpg",
                "ingredients_text": "200 g pasta",
                "steps_text": "Boil.",
            },
        )
        recipe = Recipe.objects.get(title="Photo pasta")
        self.assertEqual(recipe.image_url, "https://example.com/pasta.jpg")


class EditAndDeleteTests(TestCase):
    def setUp(self):
        self.owner = make_user(username="owner")
        self.other = make_user(username="stranger")
        self.recipe = make_recipe(self.owner, title="Old title")
        self.client.force_login(self.owner)

    def test_edit_updates_the_title_everywhere(self):
        response = self.client.post(
            reverse("recipes:edit", args=[self.recipe.pk]),
            {
                "title": "New title",
                "description": "",
                "servings": 4,
                "image_url": "",
                "source_url": "",
                "ingredients_text": "flour\nwater",
                "steps_text": "Mix.",
            },
        )
        self.assertRedirects(response, reverse("recipes:detail", args=[self.recipe.pk]))
        self.recipe.refresh_from_db()
        self.assertEqual(self.recipe.title, "New title")
        self.assertContains(self.client.get(reverse("recipes:library")), "New title")

    def test_edit_prefills_ingredients_one_per_line(self):
        response = self.client.get(reverse("recipes:edit", args=[self.recipe.pk]))
        self.assertContains(response, "flour")
        self.assertContains(response, "water")

    def test_another_cook_cannot_edit(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("recipes:edit", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 404)

    def test_delete_after_confirmation(self):
        confirm = self.client.get(reverse("recipes:delete", args=[self.recipe.pk]))
        self.assertContains(confirm, "Delete")

        response = self.client.post(reverse("recipes:delete", args=[self.recipe.pk]))
        self.assertRedirects(response, reverse("recipes:library"))
        self.assertEqual(Recipe.objects.count(), 0)
        self.assertEqual(self.client.get(reverse("recipes:detail", args=[self.recipe.pk])).status_code, 404)


class NutritionOverrideTests(TestCase):
    def setUp(self):
        self.owner = make_user(username="owner")
        self.other = make_user(username="stranger")
        self.recipe = make_recipe(self.owner, title="Chicken traybake", servings=4)
        self.client.force_login(self.owner)

    def test_override_replaces_the_figures_and_batch_recalculates(self):
        response = self.client.post(
            reverse("recipes:nutrition", args=[self.recipe.pk]),
            {"calories": 400, "protein_g": 20, "carbs_g": 30, "fat_g": 12},
        )
        self.assertRedirects(response, reverse("recipes:detail", args=[self.recipe.pk]))
        self.recipe.refresh_from_db()
        self.assertEqual(self.recipe.nutrition_override["calories"], 400)

        detail = self.client.get(reverse("recipes:detail", args=[self.recipe.pk]))
        self.assertContains(detail, "400")
        self.assertContains(detail, "1,600")
        self.assertContains(detail, "Manual figures")
        # The imported numbers are preserved underneath the override.
        self.assertEqual(self.recipe.nutrition["calories"], 320)

    def test_clearing_the_override_restores_imported_figures(self):
        self.recipe.nutrition_override = {"calories": 400}
        self.recipe.save()

        self.client.post(reverse("recipes:nutrition_clear", args=[self.recipe.pk]))
        self.recipe.refresh_from_db()
        self.assertEqual(self.recipe.nutrition_override, {})
        detail = self.client.get(reverse("recipes:detail", args=[self.recipe.pk]))
        self.assertContains(detail, "320")
        self.assertContains(detail, "Imported figures")

    def test_non_numeric_override_shows_the_error_at_the_field(self):
        response = self.client.post(
            reverse("recipes:nutrition", args=[self.recipe.pk]), {"calories": "lots"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a number")
        self.recipe.refresh_from_db()
        self.assertEqual(self.recipe.nutrition_override, {})

    def test_override_on_a_foreign_recipe_is_a_404(self):
        self.client.force_login(self.other)
        response = self.client.post(
            reverse("recipes:nutrition", args=[self.recipe.pk]), {"calories": 100}
        )
        self.assertEqual(response.status_code, 404)
        self.recipe.refresh_from_db()
        self.assertEqual(self.recipe.nutrition_override, {})
