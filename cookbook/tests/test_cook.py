"""Cook-along screen: every step is rendered for tap, keyboard and voice paging."""

from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from cookbook.tests.factories import make_recipe, make_user

APP_JS = Path(settings.BASE_DIR) / "static" / "js" / "app.js"


class CookAlongTests(TestCase):
    def setUp(self):
        self.owner = make_user(username="owner")
        self.other = make_user(username="stranger")

    def test_every_step_renders_with_the_pager_hooks(self):
        recipe = make_recipe(
            self.owner, title="Five step stew", steps=["One", "Two", "Three", "Four", "Five"]
        )
        self.client.force_login(self.owner)
        response = self.client.get(reverse("recipes:cook", args=[recipe.pk]))
        self.assertEqual(response.status_code, 200)

        html = response.content.decode()
        # The stage, the counter and one element per step.
        self.assertIn("data-cook-along", html)
        self.assertEqual(html.count("data-cook-step="), 5)
        self.assertContains(response, "Step 1 of 5")
        for step in ("One", "Two", "Three", "Four", "Five"):
            self.assertContains(response, f">{step}<")
        # Only the first step is visible on first paint.
        self.assertEqual(html.count('data-active="true"'), 1)

        # Tap zones.
        self.assertIn('data-cook-action="back"', html)
        self.assertIn('data-cook-action="repeat"', html)
        self.assertIn('data-cook-action="next"', html)

        # Hands-free (voice) control plus its live status line.
        self.assertIn("data-voice-toggle", html)
        self.assertIn('aria-pressed="false"', html)
        self.assertIn("data-voice-status", html)
        self.assertIn('aria-live="polite"', html)
        self.assertContains(response, "Hands-free")
        self.assertContains(response, "arrow keys")

        # A progress indicator with real ARIA values.
        self.assertIn("data-cook-progressbar", html)
        self.assertIn('role="progressbar"', html)
        self.assertIn('aria-valuemax="5"', html)

    def test_shipped_script_implements_tap_keyboard_and_voice_paging(self):
        script = APP_JS.read_text(encoding="utf-8")

        # Paging engine.
        self.assertIn("function initCookAlong", script)
        self.assertIn("[data-cook-step]", script)
        self.assertIn("data-active", script)
        self.assertIn("data-cook-counter", script)
        self.assertIn("data-cook-progress", script)

        # Keyboard paging.
        self.assertIn("ArrowRight", script)
        self.assertIn("ArrowLeft", script)

        # Tap paging.
        self.assertIn('data-cook-action', script)
        self.assertIn('"next"', script)
        self.assertIn('"back"', script)
        self.assertIn('"repeat"', script)

        # Voice paging with a visible status line and a graceful fallback.
        self.assertIn("SpeechRecognition", script)
        self.assertIn("webkitSpeechRecognition", script)
        self.assertIn("data-voice-toggle", script)
        self.assertIn("data-voice-status", script)
        self.assertIn("Listening — say next, back or repeat.", script)
        self.assertIn("Heard: next", script)
        self.assertIn("not available in this browser", script)

    def test_recipe_without_steps_invites_the_owner_to_write_them(self):
        recipe = make_recipe(self.owner, title="Empty method", steps=[])
        self.client.force_login(self.owner)
        response = self.client.get(reverse("recipes:cook", args=[recipe.pk]))
        self.assertContains(response, "There are no steps to cook yet")
        self.assertContains(response, reverse("recipes:edit", args=[recipe.pk]))

    def test_foreign_recipe_cook_page_is_a_404(self):
        recipe = make_recipe(self.other, title="Private stew")
        self.client.force_login(self.owner)
        self.assertEqual(
            self.client.get(reverse("recipes:cook", args=[recipe.pk])).status_code, 404
        )
