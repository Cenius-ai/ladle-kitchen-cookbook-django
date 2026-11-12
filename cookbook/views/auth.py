"""Register, sign in and sign out."""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from cookbook.forms import LoginForm, RegisterForm

DEMO_EMAIL = "cenius@cenius.ai"
DEMO_USERNAME = "cenius"
DEMO_PASSWORD = "cenius"


def safe_next(request, next_url):
    """Only follow a redirect target that stays on this host."""
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return next_url
    return ""


def login_view(request):
    if request.user.is_authenticated:
        return redirect("recipes:library")

    next_url = request.POST.get("next") or request.GET.get("next") or ""
    form = LoginForm(request.POST or None)
    form.bind_request(request)

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f"Signed in as {user.username}.")
        return redirect(safe_next(request, next_url) or "recipes:library")

    return render(
        request,
        "auth/login.html",
        {
            "form": form,
            "next": next_url,
            "demo_email": DEMO_EMAIL,
            "demo_password": DEMO_PASSWORD,
        },
    )


def register_view(request):
    if request.user.is_authenticated:
        return redirect("recipes:library")

    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome to Ladle, {user.username}.")
        return redirect("recipes:library")

    return render(request, "auth/register.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "Signed out. See you at the stove.")
    return redirect("auth:login")
