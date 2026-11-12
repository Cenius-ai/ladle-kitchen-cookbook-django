"""Collections: creation, isolation, invite codes, joining and membership."""

from django.test import TestCase
from django.urls import reverse

from cookbook.models import Collection, CollectionMember, CollectionRecipe
from cookbook.tests.factories import make_collection, make_recipe, make_user


class CollectionIndexTests(TestCase):
    def setUp(self):
        self.owner = make_user(username="owner")
        self.client.force_login(self.owner)

    def test_create_collection_lands_on_its_page(self):
        response = self.client.post(
            reverse("collections:list"), {"name": "Weeknight Suppers", "description": "Fast dinners"}
        )
        collection = Collection.objects.get(name="Weeknight Suppers")
        self.assertRedirects(response, reverse("collections:detail", args=[collection.pk]))
        self.assertEqual(collection.owner, self.owner)
        self.assertEqual(len(collection.invite_code), 10)
        self.assertTrue(collection.is_member(self.owner))

        listing = self.client.get(reverse("collections:list"))
        self.assertContains(listing, "Weeknight Suppers")
        self.assertContains(listing, "Owner")

    def test_blank_name_shows_a_name_required_message(self):
        response = self.client.post(reverse("collections:list"), {"name": "   ", "description": ""})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Give the collection a name")
        self.assertEqual(Collection.objects.count(), 0)

    def test_signed_out_visitor_is_sent_to_sign_in(self):
        self.client.logout()
        response = self.client.get(reverse("collections:list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("auth:login"), response.url)


class CollectionDetailTests(TestCase):
    def setUp(self):
        self.owner = make_user(username="owner")
        self.member = make_user(username="member")
        self.outsider = make_user(username="outsider")
        self.collection = make_collection(self.owner, name="Household", members=[self.member])

    def test_owner_sees_members_and_the_invite_panel(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("collections:detail", args=[self.collection.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Household")
        self.assertContains(response, self.collection.invite_code)
        self.assertContains(response, "Owner")
        self.assertContains(response, "Join link")
        self.assertContains(response, "This collection is empty")

    def test_non_member_gets_a_404(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("collections:detail", args=[self.collection.pk]))
        self.assertEqual(response.status_code, 404)

    def test_shared_recipe_appears_in_the_collection_grid(self):
        recipe = make_recipe(self.owner, title="Sunday roast")
        CollectionRecipe.objects.create(collection=self.collection, recipe=recipe, added_by=self.owner)
        self.client.force_login(self.member)
        response = self.client.get(reverse("collections:detail", args=[self.collection.pk]))
        self.assertContains(response, "Sunday roast")


class InviteCodeTests(TestCase):
    def setUp(self):
        self.owner = make_user(username="owner")
        self.guest = make_user(username="guest")
        self.collection = make_collection(self.owner, invite_code="OLDC0DE123")

    def test_owner_regenerating_retires_the_old_code(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("collections:invite", args=[self.collection.pk]))
        self.assertRedirects(response, reverse("collections:detail", args=[self.collection.pk]))
        self.collection.refresh_from_db()
        self.assertNotEqual(self.collection.invite_code, "OLDC0DE123")
        self.assertEqual(len(self.collection.invite_code), 10)

        self.client.force_login(self.guest)
        self.client.post(reverse("join"), {"code": "OLDC0DE123"})
        self.assertFalse(self.collection.is_member(self.guest))

        self.client.post(reverse("join"), {"code": self.collection.invite_code})
        self.assertTrue(self.collection.is_member(self.guest))

    def test_non_owner_cannot_regenerate(self):
        self.client.force_login(self.guest)
        response = self.client.post(reverse("collections:invite", args=[self.collection.pk]))
        self.assertEqual(response.status_code, 404)


class JoinFlowTests(TestCase):
    def setUp(self):
        self.owner = make_user(username="owner")
        self.guest = make_user(username="guest")
        self.collection = make_collection(self.owner, name="Household", invite_code="JOINME2024")
        self.client.force_login(self.guest)

    def test_join_page_resolves_a_pasted_link(self):
        link = f"http://testserver/join/{self.collection.invite_code}/"
        response = self.client.get(reverse("join_code", args=[self.collection.invite_code]))
        self.assertContains(response, "Household")

        response = self.client.post(reverse("join"), {"code": link})
        self.assertRedirects(response, reverse("collections:detail", args=[self.collection.pk]))
        self.assertTrue(self.collection.is_member(self.guest))
        self.assertContains(self.client.get(reverse("collections:list")), "Household")

    def test_unknown_code_says_it_is_invalid_and_keeps_the_entry(self):
        response = self.client.post(reverse("join"), {"code": "NOSUCHCODE"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "That invite code is not valid.")
        self.assertContains(response, 'value="NOSUCHCODE"')
        self.assertFalse(
            CollectionMember.objects.filter(collection=self.collection, user=self.guest).exists()
        )


class RecipeMembershipTests(TestCase):
    def setUp(self):
        self.owner = make_user(username="owner")
        self.member = make_user(username="member")
        self.outsider = make_user(username="outsider")
        self.collection = make_collection(self.owner, name="Household", members=[self.member])
        self.recipe = make_recipe(self.owner, title="Sunday roast")

    def test_member_adds_their_own_recipe_from_the_recipe_page(self):
        own_recipe = make_recipe(self.member, title="Member soup")
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("collections:add_recipe", args=[self.collection.pk]),
            {"recipe_id": own_recipe.pk},
        )
        self.assertRedirects(response, reverse("recipes:detail", args=[own_recipe.pk]))
        self.assertTrue(
            CollectionRecipe.objects.filter(collection=self.collection, recipe=own_recipe).exists()
        )

    def test_a_member_cannot_remove_someone_elses_recipe(self):
        CollectionRecipe.objects.create(collection=self.collection, recipe=self.recipe, added_by=self.owner)
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("collections:remove_recipe", args=[self.collection.pk, self.recipe.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(CollectionRecipe.objects.exists())

    def test_non_member_cannot_add_to_a_collection(self):
        self.client.force_login(self.outsider)
        response = self.client.post(
            reverse("collections:add_recipe", args=[self.collection.pk]),
            {"recipe_id": self.recipe.pk},
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(CollectionRecipe.objects.exists())

    def test_removing_a_recipe_keeps_it_in_the_library(self):
        CollectionRecipe.objects.create(collection=self.collection, recipe=self.recipe, added_by=self.member)
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("collections:remove_recipe", args=[self.collection.pk, self.recipe.pk])
        )
        self.assertRedirects(response, reverse("collections:detail", args=[self.collection.pk]))
        self.assertFalse(CollectionRecipe.objects.exists())
        self.assertTrue(self.recipe.__class__.objects.filter(pk=self.recipe.pk).exists())


class MembershipManagementTests(TestCase):
    def setUp(self):
        self.owner = make_user(username="owner")
        self.member = make_user(username="member")
        self.collection = make_collection(self.owner, name="Household", members=[self.member])

    def test_owner_removes_a_member_and_they_lose_access(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("collections:remove_member", args=[self.collection.pk, self.member.pk])
        )
        self.assertRedirects(response, reverse("collections:detail", args=[self.collection.pk]))
        self.assertFalse(self.collection.is_member(self.member))

        self.client.force_login(self.member)
        self.assertEqual(
            self.client.get(reverse("collections:detail", args=[self.collection.pk])).status_code, 404
        )

    def test_member_can_leave_but_the_owner_cannot(self):
        self.client.force_login(self.member)
        self.client.post(reverse("collections:leave", args=[self.collection.pk]))
        self.assertFalse(self.collection.is_member(self.member))

        self.client.force_login(self.owner)
        self.client.post(reverse("collections:leave", args=[self.collection.pk]))
        self.assertTrue(self.collection.is_member(self.owner))

    def test_member_cannot_remove_another_member(self):
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("collections:remove_member", args=[self.collection.pk, self.owner.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(self.collection.is_member(self.owner))
