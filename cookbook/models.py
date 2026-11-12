from django.conf import settings
from django.db import models

from cookbook.services import nutrition as nutrition_service
from cookbook.services.invites import unique_invite_code


class Recipe(models.Model):
    """A single recipe owned by one cook."""

    ORIGIN_IMPORTED = "imported"
    ORIGIN_MANUAL = "manual"
    ORIGIN_CHOICES = [
        (ORIGIN_IMPORTED, "Imported"),
        (ORIGIN_MANUAL, "Added by hand"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recipes"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    source_url = models.URLField(max_length=500, blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    servings = models.PositiveIntegerField(default=4)
    steps = models.JSONField(default=list, blank=True)
    nutrition = models.JSONField(default=dict, blank=True)
    nutrition_override = models.JSONField(default=dict, blank=True)
    origin = models.CharField(max_length=16, choices=ORIGIN_CHOICES, default=ORIGIN_MANUAL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        indexes = [models.Index(fields=["owner", "-updated_at"])]

    def __str__(self):
        return self.title

    @property
    def step_count(self):
        return len(self.steps or [])

    def per_portion_nutrition(self):
        return nutrition_service.resolve(self.nutrition, self.nutrition_override)

    def batch_nutrition(self):
        return nutrition_service.batch(self.per_portion_nutrition(), self.servings)

    def nutrition_source(self):
        return nutrition_service.source_label(self.nutrition, self.nutrition_override)

    def has_imported_nutrition(self):
        return nutrition_service.has_values(self.nutrition)

    def calories_per_portion(self):
        return self.per_portion_nutrition()["calories"]


class Ingredient(models.Model):
    """One ingredient line, kept in the cook's entered order."""

    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="ingredients")
    position = models.PositiveIntegerField(default=0)
    text = models.CharField(max_length=300)

    class Meta:
        ordering = ["position", "id"]
        indexes = [models.Index(fields=["recipe", "position"])]

    def __str__(self):
        return self.text


class Collection(models.Model):
    """A household cookbook: a named set of recipes shared by members."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_collections"
    )
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    invite_code = models.CharField(max_length=12, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = unique_invite_code(Collection)
        super().save(*args, **kwargs)

    def regenerate_invite_code(self):
        self.invite_code = unique_invite_code(Collection)
        self.save(update_fields=["invite_code"])
        return self.invite_code

    def membership(self, user):
        if not user.is_authenticated:
            return None
        return self.members.filter(user=user).first()

    def is_member(self, user):
        return self.membership(user) is not None

    def is_owner(self, user):
        return user.is_authenticated and self.owner_id == user.id

    def member_count(self):
        return self.members.count()

    def recipe_count(self):
        return self.recipe_entries.count()


class CollectionMember(models.Model):
    ROLE_OWNER = "owner"
    ROLE_MEMBER = "member"
    ROLE_CHOICES = [(ROLE_OWNER, "Owner"), (ROLE_MEMBER, "Member")]

    collection = models.ForeignKey(
        Collection, on_delete=models.CASCADE, related_name="members"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="collection_memberships"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("collection", "user")]
        ordering = ["role", "joined_at"]

    def __str__(self):
        return f"{self.user.username} in {self.collection.name}"

    @property
    def is_owner(self):
        return self.role == self.ROLE_OWNER


class CollectionRecipe(models.Model):
    collection = models.ForeignKey(
        Collection, on_delete=models.CASCADE, related_name="recipe_entries"
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="collection_entries"
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="added_collection_recipes"
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("collection", "recipe")]
        ordering = ["-added_at"]

    def __str__(self):
        return f"{self.recipe.title} in {self.collection.name}"
