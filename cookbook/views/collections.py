"""Household collections: create, share by invite code, add and remove recipes."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from cookbook.forms import CollectionForm, JoinForm
from cookbook.models import Collection, CollectionMember, CollectionRecipe
from cookbook.services.access import (
    get_visible_collection_or_404,
    get_visible_recipe_or_404,
    visible_collections,
)


def _owned_collection_or_404(user, pk):
    """Owner-only actions: a non-owner sees the same 404 as a missing row."""
    return get_object_or_404(Collection, pk=pk, owner=user)


@login_required
def index(request):
    form = CollectionForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        collection = form.save(commit=False)
        collection.owner = request.user
        collection.save()
        CollectionMember.objects.get_or_create(
            collection=collection,
            user=request.user,
            defaults={"role": CollectionMember.ROLE_OWNER},
        )
        messages.success(
            request, f"“{collection.name}” was created — share its invite code with your household."
        )
        return redirect("collections:detail", pk=collection.pk)

    collections = visible_collections(request.user).annotate(
        recipe_total=Count("recipe_entries", distinct=True),
        member_total=Count("members", distinct=True),
    )
    rows = [
        {"collection": collection, "is_owner": collection.owner_id == request.user.id}
        for collection in collections
    ]
    return render(
        request,
        "collections/list.html",
        {"rows": rows, "form": form, "join_form": JoinForm()},
    )


@login_required
def detail(request, pk):
    collection = get_visible_collection_or_404(request.user, pk)
    can_manage = collection.is_owner(request.user)

    entries = collection.recipe_entries.select_related(
        "recipe", "recipe__owner", "added_by"
    )
    rows = [
        {"entry": entry, "can_remove": can_manage or entry.added_by_id == request.user.id}
        for entry in entries
    ]

    members = collection.members.select_related("user")
    member_rows = [
        {
            "membership": membership,
            "is_owner": membership.role == CollectionMember.ROLE_OWNER,
            "can_remove": can_manage and membership.user_id != collection.owner_id,
        }
        for membership in members
    ]

    join_link = request.build_absolute_uri(
        reverse("join_code", args=[collection.invite_code])
    )
    return render(
        request,
        "collections/detail.html",
        {
            "collection": collection,
            "rows": rows,
            "member_rows": member_rows,
            "can_manage": can_manage,
            "is_member": collection.is_member(request.user),
            "join_link": join_link,
        },
    )


@login_required
@require_POST
def regenerate_invite(request, pk):
    collection = _owned_collection_or_404(request.user, pk)
    code = collection.regenerate_invite_code()
    messages.success(request, f"New invite code {code}. The old link no longer works.")
    return redirect("collections:detail", pk=collection.pk)


@login_required
@require_POST
def add_recipe(request, pk):
    collection = get_visible_collection_or_404(request.user, pk)
    recipe_id = (request.POST.get("recipe_id") or "").strip()
    if not recipe_id.isdigit():
        raise Http404("No recipe to add")
    recipe = get_visible_recipe_or_404(request.user, int(recipe_id))
    entry, created = CollectionRecipe.objects.get_or_create(
        collection=collection, recipe=recipe, defaults={"added_by": request.user}
    )
    if created:
        messages.success(request, f"“{recipe.title}” was added to {collection.name}.")
    else:
        messages.info(request, f"“{recipe.title}” is already in {collection.name}.")
    return redirect("recipes:detail", pk=recipe.pk)


@login_required
@require_POST
def remove_recipe(request, pk, recipe_pk):
    collection = get_visible_collection_or_404(request.user, pk)
    entry = get_object_or_404(CollectionRecipe, collection=collection, recipe_id=recipe_pk)
    if not (collection.is_owner(request.user) or entry.added_by_id == request.user.id):
        # Refuse loudly but without detail: the same 404 as a missing entry.
        raise Http404("No removable entry")
    title = entry.recipe.title
    entry.delete()
    messages.success(request, f"“{title}” was removed from {collection.name}.")
    return redirect("collections:detail", pk=collection.pk)


@login_required
@require_POST
def leave(request, pk):
    collection = get_visible_collection_or_404(request.user, pk)
    membership = collection.membership(request.user)
    if membership is None:
        messages.info(request, "You are not a member of that collection.")
    elif membership.user_id == collection.owner_id:
        messages.error(request, "Owners cannot leave their own collection.")
    else:
        membership.delete()
        messages.success(request, f"You left {collection.name}.")
    return redirect("collections:list")


@login_required
@require_POST
def remove_member(request, pk, user_pk):
    collection = _owned_collection_or_404(request.user, pk)
    membership = get_object_or_404(CollectionMember, collection=collection, user_id=user_pk)
    if membership.user_id == collection.owner_id:
        messages.error(request, "The owner cannot be removed from their own collection.")
    else:
        username = membership.user.username
        membership.delete()
        messages.success(request, f"{username} was removed from {collection.name}.")
    return redirect("collections:detail", pk=collection.pk)


@login_required
def join(request, code=None):
    initial_code = (code or "").strip()
    form = JoinForm(request.POST or None, initial={"code": initial_code} if initial_code else None)
    resolved = None

    if request.method == "POST" and form.is_valid():
        wanted = form.cleaned_data["code"]
        collection = Collection.objects.filter(invite_code__iexact=wanted).first()
        if collection is None:
            form.add_error("code", "That invite code is not valid.")
        else:
            _, created = CollectionMember.objects.get_or_create(
                collection=collection,
                user=request.user,
                defaults={"role": CollectionMember.ROLE_MEMBER},
            )
            if created:
                messages.success(request, f"Joined {collection.name}.")
            else:
                messages.info(request, f"You are already a member of {collection.name}.")
            return redirect("collections:detail", pk=collection.pk)
    elif initial_code:
        resolved = Collection.objects.filter(invite_code__iexact=initial_code.upper()).first()

    return render(
        request,
        "collections/join.html",
        {"form": form, "resolved": resolved, "code": initial_code},
    )
