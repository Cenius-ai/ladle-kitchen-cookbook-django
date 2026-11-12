"""Accounts: register, sign in with username or email, sign out, login wall."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cookbook.tests.factories import make_user


class RegistrationTests(TestCase):
    def test_register_signs_the_cook_in_and_lands_on_the_library(self):
        response = self.client.post(
            reverse("auth:register"),
            {
                "username": "newcook",
                "email": "new@example.com",
                "password1": "saffron-risotto",
                "password2": "saffron-risotto",
            },
        )
        self.assertRedirects(response, reverse("recipes:library"))
        user = get_user_model().objects.get(username="newcook")
        self.assertEqual(user.email, "new@example.com")
        self.assertTrue(user.check_password("saffron-risotto"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_duplicate_username_shows_an_inline_error(self):
        make_user(username="taken")
        response = self.client.post(
            reverse("auth:register"),
            {
                "username": "taken",
                "email": "other@example.com",
                "password1": "saffron-risotto",
                "password2": "saffron-risotto",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "That username is taken.")
        self.assertFalse(get_user_model().objects.filter(email="other@example.com").exists())

    def test_mismatched_passwords_keep_the_typed_username(self):
        response = self.client.post(
            reverse("auth:register"),
            {
                "username": "halfway",
                "email": "halfway@example.com",
                "password1": "saffron-risotto",
                "password2": "***REDACTED-SECRET***",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The two passwords do not match.")
        self.assertContains(response, 'value="halfway"')


class SignInTests(TestCase):
    def setUp(self):
        self.user = make_user(username="cenius", password="cenius", email="cenius@cenius.ai")

    def test_sign_in_with_the_email_address(self):
        response = self.client.post(
            reverse("auth:login"), {"identifier": "cenius@cenius.ai", "password": "cenius"}
        )
        self.assertRedirects(response, reverse("recipes:library"))

    def test_sign_in_with_the_username(self):
        response = self.client.post(
            reverse("auth:login"), {"identifier": "cenius", "password": "cenius"}
        )
        self.assertRedirects(response, reverse("recipes:library"))

    def test_wrong_password_gives_one_non_enumerating_message(self):
        response = self.client.post(
            reverse("auth:login"), {"identifier": "cenius", "password": "wrong-password"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "is not correct")
        self.assertNotContains(response, "That username is taken")
        self.assertContains(response, 'value="cenius"')

    def test_unknown_account_gives_the_same_message(self):
        response = self.client.post(
            reverse("auth:login"), {"identifier": "nobody@example.com", "password": "wrong-password"}
        )
        self.assertContains(response, "is not correct")

    def test_sign_in_page_shows_the_demo_credential(self):
        response = self.client.get(reverse("auth:login"))
        self.assertContains(response, "cenius@cenius.ai")
        self.assertContains(response, "Demo")


class AccessTests(TestCase):
    def setUp(self):
        self.user = make_user(username="locked", password="***REDACTED-SECRET***")

    def test_signed_out_visit_redirects_and_returns_to_the_requested_page(self):
        library = reverse("recipes:library")
        response = self.client.get(library)
        self.assertRedirects(response, f"{reverse('auth:login')}?next={library}")

        response = self.client.post(
            f"{reverse('auth:login')}?next={library}",
            {"identifier": "locked", "password": "***REDACTED-SECRET***", "next": library},
        )
        self.assertRedirects(response, library)

    def test_sign_out_ends_the_session(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("auth:logout"))
        self.assertRedirects(response, reverse("auth:login"))
        self.assertRedirects(self.client.get(reverse("recipes:library")), "/accounts/login/?next=/recipes/")
