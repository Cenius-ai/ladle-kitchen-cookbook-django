"""URL map for the cookbook app."""

from django.urls import include, path

from cookbook.views import auth as auth_views
from cookbook.views import collections as collection_views
from cookbook.views import cook as cook_views
from cookbook.views import home as home_views
from cookbook.views import imports as import_views
from cookbook.views import nutrition as nutrition_views
from cookbook.views import recipes as recipe_views

account_patterns = [
    path("login/", auth_views.login_view, name="login"),
    path("register/", auth_views.register_view, name="register"),
    path("logout/", auth_views.logout_view, name="logout"),
]

recipe_patterns = [
    path("", recipe_views.library, name="library"),
    path("import/", import_views.import_recipe, name="import"),
    path("new/", recipe_views.create, name="create"),
    path("<int:pk>/", recipe_views.detail, name="detail"),
    path("<int:pk>/edit/", recipe_views.edit, name="edit"),
    path("<int:pk>/delete/", recipe_views.delete, name="delete"),
    path("<int:pk>/nutrition/", nutrition_views.set_override, name="nutrition"),
    path("<int:pk>/nutrition/clear/", nutrition_views.clear_override, name="nutrition_clear"),
    path("<int:pk>/cook/", cook_views.cook, name="cook"),
]

collection_patterns = [
    path("", collection_views.index, name="list"),
    path("<int:pk>/", collection_views.detail, name="detail"),
    path("<int:pk>/invite/", collection_views.regenerate_invite, name="invite"),
    path("<int:pk>/recipes/add/", collection_views.add_recipe, name="add_recipe"),
    path(
        "<int:pk>/recipes/<int:recipe_pk>/remove/",
        collection_views.remove_recipe,
        name="remove_recipe",
    ),
    path("<int:pk>/leave/", collection_views.leave, name="leave"),
    path(
        "<int:pk>/members/<int:user_pk>/remove/",
        collection_views.remove_member,
        name="remove_member",
    ),
]

urlpatterns = [
    path("", home_views.home, name="home"),
    path("health", home_views.health, name="health"),
    path("accounts/", include((account_patterns, "auth"))),
    path("recipes/", include((recipe_patterns, "recipes"))),
    path("collections/", include((collection_patterns, "collections"))),
    path("join/", collection_views.join, name="join"),
    path("join/<str:code>/", collection_views.join, name="join_code"),
]
