# Using Ladle Kitchen Cookbook

## Overview

This is **Ladle Kitchen Cookbook** — an HTTP API + web UI. This document covers the surface area you can use, with copy-pasteable examples for each entry point. For setup, see `INSTALL.md`.

## Quickstart

After completing the install steps in `INSTALL.md`:

```bash
python manage.py runserver    # start the server
# in another terminal:
curl http://localhost:8000/
```

## Endpoints

Every endpoint below was extracted from the source by the route scanner (Next.js / FastAPI / Flask / Django / Express).

| Method | Path | Source file |
|--------|------|-------------|
| `GET` | `/` | `cookbook/urls.py` |
| `GET` | `/:pk/` | `cookbook/urls.py` |
| `GET` | `/:pk/cook/` | `cookbook/urls.py` |
| `GET` | `/:pk/delete/` | `cookbook/urls.py` |
| `GET` | `/:pk/edit/` | `cookbook/urls.py` |
| `GET` | `/:pk/invite/` | `cookbook/urls.py` |
| `GET` | `/:pk/leave/` | `cookbook/urls.py` |
| `GET` | `/:pk/members/:user_pk/remove/` | `cookbook/urls.py` |
| `GET` | `/:pk/nutrition/` | `cookbook/urls.py` |
| `GET` | `/:pk/nutrition/clear/` | `cookbook/urls.py` |
| `GET` | `/:pk/recipes/:recipe_pk/remove/` | `cookbook/urls.py` |
| `GET` | `/:pk/recipes/add/` | `cookbook/urls.py` |
| `GET` | `/accounts/` | `cookbook/urls.py` |
| `GET` | `/admin/` | `ladle/urls.py` |
| `GET` | `/collections/` | `cookbook/urls.py` |
| `GET` | `/health` | `cookbook/urls.py` |
| `GET` | `/import/` | `cookbook/urls.py` |
| `GET` | `/join/` | `cookbook/urls.py` |
| `GET` | `/join/:code/` | `cookbook/urls.py` |
| `GET` | `/login/` | `cookbook/urls.py` |
| `GET` | `/logout/` | `cookbook/urls.py` |
| `GET` | `/new/` | `cookbook/urls.py` |
| `GET` | `/recipes/` | `cookbook/urls.py` |
| `GET` | `/register/` | `cookbook/urls.py` |

### curl examples

#### `GET /`

```bash
curl http://localhost:8000/
```

#### `GET /:pk/`

```bash
curl http://localhost:8000/<pk>/
```

#### `GET /:pk/cook/`

```bash
curl http://localhost:8000/<pk>/cook/
```

#### `GET /:pk/delete/`

```bash
curl http://localhost:8000/<pk>/delete/
```

#### `GET /:pk/edit/`

```bash
curl http://localhost:8000/<pk>/edit/
```

## Worked example

1. Boot the server (`python manage.py runserver`).
2. Hit a smoke-test endpoint:

```bash
curl -sS http://localhost:8000/
```

3. If you get a JSON / HTML response, the server is healthy. Inspect `.env` if it errors with an auth/config failure.

## Reference

### Entry points

_No explicit entry points declared in this project's manifests._

### Surface index (auto-extracted)

| Kind | Title | Source file |
|------|-------|-------------|
| route | `/` | `cookbook/urls.py` |
| route | `/:pk/` | `cookbook/urls.py` |
| route | `/:pk/cook/` | `cookbook/urls.py` |
| route | `/:pk/delete/` | `cookbook/urls.py` |
| route | `/:pk/edit/` | `cookbook/urls.py` |
| route | `/:pk/invite/` | `cookbook/urls.py` |
| route | `/:pk/leave/` | `cookbook/urls.py` |
| route | `/:pk/members/:user_pk/remove/` | `cookbook/urls.py` |
| route | `/:pk/nutrition/` | `cookbook/urls.py` |
| route | `/:pk/nutrition/clear/` | `cookbook/urls.py` |
| route | `/:pk/recipes/:recipe_pk/remove/` | `cookbook/urls.py` |
| route | `/:pk/recipes/add/` | `cookbook/urls.py` |
| route | `/accounts/` | `cookbook/urls.py` |
| route | `/admin/` | `ladle/urls.py` |
| route | `/collections/` | `cookbook/urls.py` |
| route | `/health` | `cookbook/urls.py` |
| route | `/import/` | `cookbook/urls.py` |
| route | `/join/` | `cookbook/urls.py` |
| route | `/join/:code/` | `cookbook/urls.py` |
| route | `/login/` | `cookbook/urls.py` |
| route | `/logout/` | `cookbook/urls.py` |
| route | `/new/` | `cookbook/urls.py` |
| route | `/recipes/` | `cookbook/urls.py` |
| route | `/register/` | `cookbook/urls.py` |

## Next steps

- Read [INSTALL.md](./INSTALL.md) if anything in the Quickstart didn't work.
- Inspect `.env.example` for the full list of environment variables this project understands.
- See [README.md](./README.md) for the architecture diagram + feature list.
