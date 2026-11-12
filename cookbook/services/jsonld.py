"""Turn pasted schema.org Recipe JSON-LD into plain recipe data.

The import screen accepts three shapes, because that is what recipe sites and
browser extensions actually emit:

* a bare ``{"@type": "Recipe", ...}`` object,
* a full ``<script type="application/ld+json">`` block,
* an ``@graph`` array holding a WebPage and a Recipe side by side.

Everything is pure Python and offline: nothing is fetched, the paste is the
only input.
"""

import html
import json
import re
from dataclasses import dataclass, field

from cookbook.services import nutrition

_SCRIPT_RE = re.compile(
    r"<script[^>]*type\s*=\s*[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_INT_RE = re.compile(r"\d+")

MAX_INGREDIENTS = 100
MAX_STEPS = 80


class JsonLdError(ValueError):
    """Raised when a paste cannot be turned into a usable Recipe."""


@dataclass
class ParsedRecipe:
    """Recipe fields extracted from a JSON-LD node, before anything is saved."""

    title: str
    description: str = ""
    source_url: str = ""
    image_url: str = ""
    servings: int = 4
    ingredients: list = field(default_factory=list)
    steps: list = field(default_factory=list)
    nutrition: dict = field(default_factory=dict)

    @property
    def ingredient_count(self):
        return len(self.ingredients)

    @property
    def step_count(self):
        return len(self.steps)

    @property
    def has_nutrition(self):
        return nutrition.has_values(self.nutrition)

    def nutrition_rows(self):
        """(label, value, unit) triples for the preview and the save call."""
        rows = []
        for key in nutrition.NUTRIENT_FIELDS:
            value = self.nutrition.get(key)
            if value is None:
                continue
            rows.append(
                (
                    nutrition.NUTRIENT_LABELS[key],
                    f"{value:.0f}" if float(value).is_integer() else f"{value:.1f}",
                    nutrition.NUTRIENT_UNITS[key],
                )
            )
        return rows


def clean_text(value):
    """Flatten an instruction or description into plain, single-spaced text."""
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        value = value.get("text") or value.get("name") or ""
    if not isinstance(value, str):
        return ""
    text = html.unescape(_TAG_RE.sub(" ", value))
    return _WS_RE.sub(" ", text).strip()


def _type_names(node):
    if not isinstance(node, dict):
        return set()
    raw = node.get("@type") or node.get("type") or []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return set()
    return {str(item).strip().lower() for item in raw}


def _iter_nodes(document):
    """Yield every dict in a JSON document, depth first."""
    stack = [document]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            yield node
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)


def _find_recipe(document):
    for node in _iter_nodes(document):
        if "recipe" in _type_names(node):
            return node
    return None


def _first_string(value):
    """Pull the first usable string out of a string / list / ImageObject."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        for item in value:
            found = _first_string(item)
            if found:
                return found
        return ""
    if isinstance(value, dict):
        for key in ("url", "contentUrl", "@id", "name"):
            if key in value:
                found = _first_string(value[key])
                if found:
                    return found
    return ""


def _servings(value):
    """Read recipeYield in its string, number or list shape."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, float):
        return int(value) if value >= 1 else None
    if isinstance(value, list):
        for item in value:
            found = _servings(item)
            if found:
                return found
        return None
    if isinstance(value, str):
        match = _INT_RE.search(value)
        if match:
            number = int(match.group(0))
            if 0 < number <= 200:
                return number
    return None


def _collect_steps(value, collected):
    """Flatten instructions in every shape: str, HowToStep, HowToSection."""
    if len(collected) >= MAX_STEPS:
        return
    if value is None:
        return
    if isinstance(value, str):
        for line in value.splitlines():
            text = clean_text(line)
            if text and len(collected) < MAX_STEPS:
                collected.append(text[:1000])
        return
    if isinstance(value, list):
        for item in value:
            _collect_steps(item, collected)
        return
    if isinstance(value, dict):
        # HowToSection keeps its steps in itemListElement.
        if value.get("itemListElement") or value.get("steps"):
            _collect_steps(value.get("itemListElement") or value.get("steps"), collected)
            return
        text = clean_text(value.get("text") or value.get("name") or "")
        if text and len(collected) < MAX_STEPS:
            collected.append(text[:1000])


def _collect_ingredients(value):
    lines = []
    if isinstance(value, str):
        value = value.splitlines()
    if not isinstance(value, list):
        return lines
    for item in value:
        text = clean_text(item)
        if text:
            lines.append(text[:300])
        if len(lines) >= MAX_INGREDIENTS:
            break
    return lines


def _documents(raw_text):
    """Parse every JSON-LD payload in the paste; raise if none of them parse."""
    blocks = [match.group(1) for match in _SCRIPT_RE.finditer(raw_text)]
    candidates = blocks or [raw_text]
    documents = []
    first_error = None
    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate:
            continue
        try:
            documents.append(json.loads(candidate))
        except json.JSONDecodeError as exc:
            if first_error is None:
                first_error = exc
    if not documents:
        if not blocks and not raw_text.lstrip().startswith(("{", "[")):
            raise JsonLdError(
                "No Recipe JSON-LD was found in that paste. Copy the "
                '<script type="application/ld+json"> block from the recipe page.'
            )
        detail = f" ({first_error.msg} at line {first_error.lineno})" if first_error else ""
        raise JsonLdError(f"Could not read that JSON{detail}. Check that the whole block was pasted.")
    return documents


def parse_recipe(raw_text):
    """Return a :class:`ParsedRecipe` from pasted JSON-LD text."""
    if not raw_text or not str(raw_text).strip():
        raise JsonLdError("Paste the recipe JSON-LD first, then press Parse.")

    node = None
    for document in _documents(raw_text):
        node = _find_recipe(document)
        if node is not None:
            break

    if node is None:
        raise JsonLdError(
            "No schema.org Recipe was found in that JSON. A Recipe needs an "
            "@type of Recipe and a name field."
        )

    title = clean_text(node.get("name") or node.get("headline"))
    if not title:
        raise JsonLdError("The pasted Recipe is missing the required name field.")

    ingredients = _collect_ingredients(node.get("recipeIngredient") or node.get("ingredients"))
    if not ingredients:
        raise JsonLdError(
            "The pasted Recipe is missing the required recipeIngredient field."
        )

    steps = []
    _collect_steps(node.get("recipeInstructions") or node.get("instructions"), steps)

    return ParsedRecipe(
        title=title[:200],
        description=clean_text(node.get("description"))[:2000],
        source_url=_first_string(node.get("url"))[:200],
        image_url=_first_string(node.get("image") or node.get("thumbnailUrl"))[:500],
        servings=_servings(node.get("recipeYield")) or 4,
        ingredients=ingredients,
        steps=steps,
        nutrition=nutrition.from_schema_org(node.get("nutrition")),
    )
