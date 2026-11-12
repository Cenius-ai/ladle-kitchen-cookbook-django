from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("cookbook.urls")),
]

handler404 = "cookbook.views.home.not_found"
