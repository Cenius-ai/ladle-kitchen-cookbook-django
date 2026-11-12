"""Seed the demo household: two cooks, six recipes and two shared collections.

Re-running is safe: cooks are keyed on username, collections on (owner, name)
and recipes on (owner, title). Nothing is duplicated and the demo credentials
keep working.
"""

import json
from datetime import timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from cookbook.models import (
    Collection,
    CollectionMember,
    CollectionRecipe,
    Ingredient,
    Recipe,
)
from cookbook.services.jsonld import JsonLdError, parse_recipe

SEED_FILE = Path(__file__).resolve().parent.parent.parent / "seed" / "recipes.json"

DEMO_EMAIL = "cenius@cenius.ai"


class Command(BaseCommand):
    help = "Create the demo cooks, recipes and shared collections (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Print only the final summary line (used by the runserver self-heal).",
        )

    def handle(self, *args, **options):
        quiet = options.get("quiet", False)
        if not SEED_FILE.exists():
            raise CommandError(f"Seed data file missing: {SEED_FILE}")

        try:
            data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"Seed data is not valid JSON: {exc}") from exc

        created = {"cooks": 0, "collections": 0, "recipes": 0}

        with transaction.atomic():
            cooks = self.seed_cooks(data.get("cooks", []), created, quiet)
            collections = self.seed_collections(data.get("collections", []), cooks, created, quiet)
            self.seed_recipes(data.get("recipes", []), cooks, collections, created, quiet)

        if created["cooks"] or created["collections"] or created["recipes"]:
            summary = (
                f"Seeded {created['cooks']} cook(s), {created['collections']} collection(s) "
                f"and {created['recipes']} recipe(s)."
            )
        else:
            summary = "Nothing new — the demo household is already seeded."

        self.stdout.write(self.style.SUCCESS(summary))
        self.stdout.write(
            f"Sign in as {DEMO_EMAIL} (username: cenius). The password is shown on the "
            "sign-in card and in the README."
        )

    def seed_cooks(self, specs, created, quiet):
        user_model = get_user_model()
        cooks = {}
        for spec in specs:
            user, was_created = user_model.objects.get_or_create(
                username=spec["username"],
                defaults={"email": spec.get("email", "")},
            )
            changed = was_created
            # Keep the demo account usable even after a partial earlier run.
            if not user.check_password(spec["password"]):
                user.set_password(spec["password"])
                changed = True
            if spec.get("email") and user.email != spec["email"]:
                user.email = spec["email"]
                changed = True
            if spec.get("first_name") and user.first_name != spec["first_name"]:
                user.first_name = spec["first_name"]
                changed = True
            for flag in ("is_staff", "is_superuser"):
                if spec.get(flag) and not getattr(user, flag):
                    setattr(user, flag, True)
                    changed = True
            if changed:
                user.save()
            if was_created:
                created["cooks"] += 1
                if not quiet:
                    self.stdout.write(f"  cook      + {user.username}")
            cooks[spec["username"]] = user
        return cooks

    def seed_collections(self, specs, cooks, created, quiet):
        collections = {}
        now = timezone.now()
        for spec in specs:
            owner = cooks[spec["owner"]]
            collection, was_created = Collection.objects.get_or_create(
                owner=owner,
                name=spec["name"],
                defaults={
                    "description": spec.get("description", ""),
                    "invite_code": spec["invite_code"],
                },
            )
            if was_created:
                created["collections"] += 1
                # Spread the seeded creation dates over recent weeks.
                Collection.objects.filter(pk=collection.pk).update(
                    created_at=now - timedelta(days=21 + len(collections) * 6)
                )
                if not quiet:
                    self.stdout.write(f"  collection + {collection.name} ({collection.invite_code})")

            CollectionMember.objects.get_or_create(
                collection=collection,
                user=owner,
                defaults={"role": CollectionMember.ROLE_OWNER},
            )
            for username in spec.get("members", []):
                member = cooks.get(username)
                if member is None or member.id == owner.id:
                    continue
                CollectionMember.objects.get_or_create(
                    collection=collection,
                    user=member,
                    defaults={"role": CollectionMember.ROLE_MEMBER},
                )
            collections[spec["key"]] = collection
        return collections

    def seed_recipes(self, specs, cooks, collections, created, quiet):
        now = timezone.now()
        for spec in specs:
            owner = cooks[spec["owner"]]
            try:
                parsed = parse_recipe(json.dumps(spec["jsonld"]))
            except JsonLdError as exc:
                raise CommandError(f"Seed recipe “{spec['jsonld'].get('name')}” failed to parse: {exc}") from exc

            recipe, was_created = Recipe.objects.get_or_create(
                owner=owner,
                title=parsed.title,
                defaults={
                    "description": parsed.description,
                    "source_url": parsed.source_url,
                    "image_url": parsed.image_url,
                    "servings": parsed.servings,
                    "steps": parsed.steps,
                    "nutrition": parsed.nutrition,
                    "origin": Recipe.ORIGIN_IMPORTED,
                },
            )
            if was_created:
                Ingredient.objects.bulk_create(
                    [
                        Ingredient(recipe=recipe, position=index, text=text)
                        for index, text in enumerate(parsed.ingredients)
                    ]
                )
                when = now - timedelta(days=spec.get("updated_days_ago", 5))
                Recipe.objects.filter(pk=recipe.pk).update(
                    created_at=when - timedelta(days=9), updated_at=when
                )
                created["recipes"] += 1
                if not quiet:
                    self.stdout.write(
                        f"  recipe    + {recipe.title} ({len(parsed.ingredients)} lines, {len(parsed.steps)} steps)"
                    )

            for key in spec.get("collections", []):
                collection = collections.get(key)
                if collection is None:
                    continue
                CollectionRecipe.objects.get_or_create(
                    collection=collection,
                    recipe=recipe,
                    defaults={"added_by": owner},
                )
