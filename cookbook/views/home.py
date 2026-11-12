"""Root and health endpoints."""

from django.http import HttpResponse
from django.shortcuts import redirect, render


def home(request):
    if request.user.is_authenticated:
        return redirect("recipes:library")
    return redirect("auth:login")


def health(request):
    return HttpResponse("ok", content_type="text/plain")


def not_found(request, exception):
    """404 inside the app shell (used when DEBUG is off)."""
    return render(request, "404.html", status=404)
