"""Unit tests for the schema.org Recipe JSON-LD parser."""

import json

from django.test import SimpleTestCase

from cookbook.services.jsonld import JsonLdError, parse_recipe

BARE_RECIPE = {
    "@context": "https://schema.org",
    "@type": "Recipe",
    "name": "Lemon-garlic roast chicken",
    "description": "<p>One tray, crispy skin.</p>",
    "url": "https://example.com/recipes/chicken",
    "recipeYield": "4 servings",
    "recipeIngredient": ["1 chicken", "2 lemons", "4 garlic cloves"],
    "recipeInstructions": [
        {"@type": "HowToStep", "text": "Heat the oven."},
        {"@type": "HowToStep", "text": "Roast for 55 minutes."},
    ],
    "nutrition": {
        "@type": "NutritionInformation",
        "calories": "620 kcal",
        "proteinContent": "46 g",
        "carbohydrateContent": "38 g",
        "fatContent": "29 g",
    },
}

GRAPH_PAGE = {
    "@context": "https://schema.org",
    "@graph": [
        {"@type": "WebPage", "name": "A recipe page"},
        {
            "@type": "Recipe",
            "name": "Nested section chilli",
            "recipeYield": ["6 servings"],
            "recipeIngredient": ["onion", "beans", "chipotle"],
            "recipeInstructions": [
                {
                    "@type": "HowToSection",
                    "name": "Base",
                    "itemListElement": [
                        {"@type": "HowToStep", "text": "Soften the onion."},
                        {"@type": "HowToStep", "text": "Bloom the chipotle."},
                    ],
                },
                {
                    "@type": "HowToSection",
                    "name": "Finish",
                    "itemListElement": [{"@type": "HowToStep", "text": "Simmer for 25 minutes."}],
                },
            ],
        },
    ],
}


class BareObjectTests(SimpleTestCase):
    def test_reads_title_ingredients_and_one_step_per_howtostep(self):
        parsed = parse_recipe(json.dumps(BARE_RECIPE))

        self.assertEqual(parsed.title, "Lemon-garlic roast chicken")
        self.assertEqual(parsed.ingredients, ["1 chicken", "2 lemons", "4 garlic cloves"])
        self.assertEqual(len(parsed.steps), 2)
        self.assertEqual(parsed.steps[1], "Roast for 55 minutes.")
        self.assertEqual(parsed.servings, 4)
        self.assertEqual(parsed.source_url, "https://example.com/recipes/chicken")

    def test_strips_html_from_description(self):
        parsed = parse_recipe(json.dumps(BARE_RECIPE))
        self.assertEqual(parsed.description, "One tray, crispy skin.")

    def test_nutrition_is_parsed_from_strings(self):
        parsed = parse_recipe(json.dumps(BARE_RECIPE))
        self.assertEqual(parsed.nutrition["calories"], 620)
        self.assertEqual(parsed.nutrition["protein_g"], 46)
        self.assertTrue(parsed.has_nutrition)
        self.assertEqual(parsed.nutrition_rows()[0], ("Calories", "620", "kcal"))

    def test_accepts_a_script_tag_paste(self):
        paste = f'<html><body><script type="application/ld+json">{json.dumps(BARE_RECIPE)}</script></body></html>'
        parsed = parse_recipe(paste)
        self.assertEqual(parsed.title, "Lemon-garlic roast chicken")

    def test_accepts_plain_string_instructions(self):
        recipe = dict(BARE_RECIPE, recipeInstructions="Heat the oven.\nRoast for 55 minutes.")
        parsed = parse_recipe(json.dumps(recipe))
        self.assertEqual(parsed.steps, ["Heat the oven.", "Roast for 55 minutes."])


class GraphTests(SimpleTestCase):
    def test_selects_recipe_node_and_flattens_sections(self):
        parsed = parse_recipe(json.dumps(GRAPH_PAGE))

        self.assertEqual(parsed.title, "Nested section chilli")
        self.assertEqual(
            parsed.steps,
            ["Soften the onion.", "Bloom the chipotle.", "Simmer for 25 minutes."],
        )
        self.assertEqual(parsed.servings, 6)


class ErrorTests(SimpleTestCase):
    def test_product_only_paste_names_the_missing_name_field(self):
        paste = json.dumps({"@type": "Product", "name": "A tin of beans"})
        with self.assertRaises(JsonLdError) as caught:
            parse_recipe(paste)
        self.assertIn("name", str(caught.exception))

    def test_recipe_without_ingredients_names_the_ingredient_field(self):
        paste = json.dumps({"@type": "Recipe", "name": "Mystery soup"})
        with self.assertRaises(JsonLdError) as caught:
            parse_recipe(paste)
        self.assertIn("recipeIngredient", str(caught.exception))

    def test_malformed_json_reports_could_not_read(self):
        with self.assertRaises(JsonLdError) as caught:
            parse_recipe('{"@type": "Recipe", "name": ')
        self.assertIn("Could not read that JSON", str(caught.exception))

    def test_html_without_jsonld_reports_no_recipe_found(self):
        with self.assertRaises(JsonLdError) as caught:
            parse_recipe("<html><body><h1>Just a page</h1></body></html>")
        self.assertIn("No Recipe JSON-LD was found", str(caught.exception))

    def test_empty_paste_is_rejected(self):
        with self.assertRaises(JsonLdError):
            parse_recipe("   ")
