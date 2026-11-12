"""Invite codes for household collections.

A code is short, unambiguous (no O/0 or I/1) and safe to paste into the join
form or a link. Codes are unique per collection.
"""

import secrets

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 10


def generate_invite_code():
    """Return a random 10 character invite code."""
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def unique_invite_code(model, field="invite_code"):
    """Return a code no row of ``model`` is using yet."""
    for _ in range(20):
        code = generate_invite_code()
        if not model.objects.filter(**{field: code}).exists():
            return code
    raise RuntimeError("Could not allocate a unique invite code")
