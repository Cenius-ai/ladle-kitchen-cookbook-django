# Installing Ladle Kitchen Cookbook

Ladle is a single Django service with one SQLite file. There is one package
manager in play — pip, against `requirements.txt` — and no other sub-project to
install.

## Prerequisites

- Python 3.11 or newer (`python3 --version`)
- pip for that interpreter (`python3 -m pip --version`)

Nothing else is required: no database server, no Node, no system packages. Fonts
and all static assets are committed to the repository.

## 1. Install, migrate and seed

```bash
sh install.sh
```

That one script:

1. upgrades pip/setuptools/wheel and installs `requirements.txt`,
2. writes `.env` with a freshly generated `SECRET_KEY` if `.env` is missing,
3. applies the migrations (`python3 manage.py migrate --noinput`),
4. seeds the demo household (`python3 manage.py seed`),
5. runs `python3 manage.py check` and exits.

It is safe to re-run: the seed is idempotent and keyed on usernames, collection
names and recipe titles.

If you prefer to run the steps by hand:

```bash
python3 -m pip install -r requirements.txt
python3 manage.py migrate --noinput
python3 manage.py seed
```

## 2. Run in development

```bash
python3 manage.py runserver 0.0.0.0:8000
```

Open <http://localhost:8000/>. The root URL redirects to the sign-in card, then
to the recipe library once you are signed in.

To use another port, pass it to runserver (`python3 manage.py runserver
0.0.0.0:${PORT}`), or keep the default 8000.

## 3. Sign in

| Username | Email | Password |
| --- | --- | --- |
| `cenius` | `cenius@cenius.ai` | `cenius` |
| `marta` | `marta@ladle.local` | `marta-ladle` |

The sign-in card prints `cenius@cenius.ai` and has a one-click demo sign-in
button.

## 4. Verify

```bash
python3 manage.py test          # 73 tests, no network
# or, equivalently:
pytest -q
```

Then click through: library → open a recipe → **Start cook-along** → back to the
library → **Paste JSON-LD** → paste a recipe block → **Parse** → **Save recipe**
→ **Collections** → open Weeknight Suppers → **Join with a code** as `marta`.

## Resetting the data

```bash
rm ladle.sqlite3
python3 manage.py migrate --noinput
python3 manage.py seed
```

## Production notes

- Set `DJANGO_DEBUG=false` and a real `SECRET_KEY` in the environment.
- Tighten `ALLOWED_HOSTS` in `ladle/settings.py` to your domain.
- Terminate TLS in front of the app; then enable `SECURE_SSL_REDIRECT` and the
  secure-cookie flags if you serve HTTPS only.
- Remove the demo accounts created by the seed before exposing the app.
- Static files: with `DJANGO_DEBUG=false`, run `python3 manage.py collectstatic`
  and serve `staticfiles/` from your web server.
