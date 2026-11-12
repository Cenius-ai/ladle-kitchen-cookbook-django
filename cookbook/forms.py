"""Forms for accounts, recipes, nutrition, collections and joining."""

import re

from django import forms
from django.contrib.auth import authenticate, get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

from cookbook.models import Collection, Ingredient, Recipe
from cookbook.services import nutrition as nutrition_service

USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]{3,30}$")

MAX_INGREDIENT_LINES = 100
MAX_STEP_LINES = 80

WRONG_CREDENTIALS = "That username/email and password combination is not correct."


def split_lines(value, limit):
    """Turn one-per-line text into a clean list, dropping blanks and overflow."""
    lines = []
    for raw_line in (value or "").splitlines():
        line = " ".join(raw_line.split())
        if line:
            lines.append(line[:300])
        if len(lines) >= limit:
            break
    return lines


def normalise_url(value):
    """Accept scheme-less pastes by assuming https://, then validate."""
    value = (value or "").strip()
    if not value:
        return ""
    if "://" not in value:
        value = f"https://{value}"
    URLValidator(schemes=["http", "https"])(value)
    return value[:500]


class LoginForm(forms.Form):
    """Sign in with either the username or the account email address."""

    identifier = forms.CharField(
        label="Username or email",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "autofocus": True,
                "placeholder": "cenius@cenius.ai",
                "autocapitalize": "none",
                "spellcheck": "false",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={"autocomplete": "current-password", "placeholder": "••••••••"}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None

    def clean(self):
        cleaned = super().clean()
        identifier = (cleaned.get("identifier") or "").strip()
        password = cleaned.get("password")
        if not identifier or not password:
            return cleaned

        user_model = get_user_model()
        match = (
            user_model.objects.filter(username__iexact=identifier).first()
            or user_model.objects.filter(email__iexact=identifier).first()
        )
        username = match.username if match else identifier
        authenticated = authenticate(self.request, username=username, password=password)
        if authenticated is None:
            # One message for both wrong-user and wrong-password: no account
            # enumeration from the sign-in card.
            raise ValidationError(WRONG_CREDENTIALS, code="invalid_login")
        self.user = authenticated
        return cleaned

    @property
    def request(self):
        return getattr(self, "_request", None)

    def bind_request(self, request):
        self._request = request
        return self

    def get_user(self):
        return self.user


class RegisterForm(forms.Form):
    username = forms.CharField(
        label="Username",
        max_length=30,
        widget=forms.TextInput(
            attrs={"autocomplete": "username", "autocapitalize": "none", "spellcheck": "false"}
        ),
        help_text="Letters, numbers, hyphens and underscores — 3 to 30 characters.",
    )
    email = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autocapitalize": "none"}),
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="At least 8 characters.",
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean_username(self):
        username = (self.cleaned_data["username"] or "").strip()
        if not USERNAME_RE.match(username):
            raise ValidationError(
                "Use 3 to 30 letters, numbers, hyphens or underscores.", code="invalid_username"
            )
        if get_user_model().objects.filter(username__iexact=username).exists():
            raise ValidationError("That username is taken.", code="duplicate_username")
        return username

    def clean_email(self):
        email = (self.cleaned_data["email"] or "").strip().lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise ValidationError("That email already has an account.", code="duplicate_email")
        return email

    def clean_password1(self):
        password = self.cleaned_data.get("password1") or ""
        if password:
            password_validation.validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The two passwords do not match.")
        return cleaned

    def save(self):
        return get_user_model().objects.create_user(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password1"],
        )


class RecipeForm(forms.ModelForm):
    """Create or edit a recipe; ingredients and steps arrive one per line."""

    servings = forms.IntegerField(
        label="Servings",
        min_value=1,
        max_value=100,
        initial=4,
        widget=forms.NumberInput(attrs={"min": 1, "max": 100, "inputmode": "numeric"}),
        help_text="How many portions the ingredient list makes.",
    )
    image_url = forms.CharField(
        label="Cover image URL",
        required=False,
        max_length=500,
        widget=forms.URLInput(attrs={"placeholder": "https://example.com/photo.jpg"}),
        help_text="Optional. Leave blank for the Ladle placeholder art.",
    )
    source_url = forms.CharField(
        label="Source URL",
        required=False,
        max_length=500,
        widget=forms.URLInput(attrs={"placeholder": "https://example.com/the-original-recipe"}),
        help_text="Optional. Where the recipe came from.",
    )
    ingredients_text = forms.CharField(
        label="Ingredients",
        required=True,
        widget=forms.Textarea(
            attrs={"rows": 8, "placeholder": "400 g new potatoes\n2 tbsp olive oil\n1 lemon"}
        ),
        help_text="One ingredient per line.",
        error_messages={"required": "Add at least one ingredient, one per line."},
    )
    steps_text = forms.CharField(
        label="Steps",
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 8, "placeholder": "Heat the oven to 200C.\nToss the potatoes in oil."}
        ),
        help_text="One step per line. You can add these later.",
    )

    class Meta:
        model = Recipe
        fields = ["title", "description", "servings", "image_url", "source_url"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Lemon-garlic roast chicken"}),
            "description": forms.Textarea(
                attrs={"rows": 3, "placeholder": "A short note about this recipe."}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["ingredients_text"].initial = "\n".join(
                ingredient.text for ingredient in self.instance.ingredients.all()
            )
            self.fields["steps_text"].initial = "\n".join(self.instance.steps or [])
        if "title" in self.fields:
            self.fields["title"].widget.attrs.setdefault("autofocus", True)

    def clean_title(self):
        title = " ".join((self.cleaned_data["title"] or "").split())
        if not title:
            raise ValidationError("Give the recipe a title.", code="required")
        return title[:200]

    def clean_image_url(self):
        return normalise_url(self.cleaned_data.get("image_url"))

    def clean_source_url(self):
        return normalise_url(self.cleaned_data.get("source_url"))

    def clean_ingredients_text(self):
        ingredients = split_lines(self.cleaned_data.get("ingredients_text"), MAX_INGREDIENT_LINES)
        if not ingredients:
            raise ValidationError("Add at least one ingredient, one per line.")
        return "\n".join(ingredients)

    def save(self, commit=True):
        recipe = super().save(commit=False)
        recipe.steps = split_lines(self.cleaned_data.get("steps_text"), MAX_STEP_LINES)
        if commit:
            recipe.save()
            self.save_ingredients(recipe)
        return recipe

    def save_ingredients(self, recipe):
        lines = split_lines(self.cleaned_data.get("ingredients_text"), MAX_INGREDIENT_LINES)
        recipe.ingredients.all().delete()
        Ingredient.objects.bulk_create(
            [Ingredient(recipe=recipe, position=index, text=text) for index, text in enumerate(lines)]
        )


class NutritionOverrideForm(forms.Form):
    """Four optional numbers that replace the imported per-portion figures."""

    calories = forms.FloatField(
        label="Calories",
        required=False,
        min_value=0,
        max_value=20000,
        widget=forms.NumberInput(attrs={"inputmode": "decimal", "step": "1", "min": 0}),
    )
    protein_g = forms.FloatField(
        label="Protein (g)",
        required=False,
        min_value=0,
        max_value=2000,
        widget=forms.NumberInput(attrs={"inputmode": "decimal", "step": "0.1", "min": 0}),
    )
    carbs_g = forms.FloatField(
        label="Carbs (g)",
        required=False,
        min_value=0,
        max_value=2000,
        widget=forms.NumberInput(attrs={"inputmode": "decimal", "step": "0.1", "min": 0}),
    )
    fat_g = forms.FloatField(
        label="Fat (g)",
        required=False,
        min_value=0,
        max_value=2000,
        widget=forms.NumberInput(attrs={"inputmode": "decimal", "step": "0.1", "min": 0}),
    )

    def clean(self):
        cleaned = super().clean()
        values = {
            field: cleaned.get(field)
            for field in nutrition_service.NUTRIENT_FIELDS
            if cleaned.get(field) is not None
        }
        if not values:
            raise ValidationError("Enter at least one per-portion figure to save an override.")
        self.values = values
        return cleaned


class CollectionForm(forms.ModelForm):
    name = forms.CharField(
        label="Name",
        max_length=80,
        error_messages={"required": "Give the collection a name."},
        widget=forms.TextInput(attrs={"placeholder": "Weeknight Suppers"}),
    )

    class Meta:
        model = Collection
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Weeknight Suppers"}),
            "description": forms.Textarea(
                attrs={"rows": 2, "placeholder": "What this collection is for (optional)."}
            ),
        }

    def clean_name(self):
        name = " ".join((self.cleaned_data["name"] or "").split())
        if not name:
            raise ValidationError("Give the collection a name.", code="required")
        if len(name) > 80:
            raise ValidationError("Keep the name under 80 characters.")
        return name


class JoinForm(forms.Form):
    code = forms.CharField(
        label="Invite code",
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "placeholder": "e.g. SUPPERS24X",
                "autocapitalize": "characters",
                "spellcheck": "false",
                "autocomplete": "off",
            }
        ),
        help_text="Paste the code — or the whole join link — from the collection owner.",
    )

    def clean_code(self):
        raw = (self.cleaned_data["code"] or "").strip()
        if "/join/" in raw:
            raw = raw.split("/join/", 1)[1]
        raw = raw.strip("/ ").strip()
        raw = re.sub(r"[^A-Za-z0-9]", "", raw).upper()
        if not raw:
            raise ValidationError("Paste the invite code from the collection owner.")
        return raw[:12]
