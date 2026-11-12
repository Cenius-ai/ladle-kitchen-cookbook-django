from django.contrib import admin

from cookbook.models import Collection, CollectionMember, CollectionRecipe, Ingredient, Recipe


class IngredientInline(admin.TabularInline):
    model = Ingredient
    extra = 0


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "servings", "origin", "updated_at")
    list_filter = ("origin", "owner")
    search_fields = ("title", "description")
    inlines = [IngredientInline]


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "invite_code", "created_at")
    search_fields = ("name", "invite_code")


admin.site.register(CollectionMember)
admin.site.register(CollectionRecipe)
