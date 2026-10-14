"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are built. What each one returns, including its empty case, is
specified under **Tool Inventory** in the README — the docstrings here match it.
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# ── Shared helpers ────────────────────────────────────────────────────────────
#
# Size matching and keyword scoring are both decided in the README's Tool
# Inventory rather than in the starter docstrings, because the data forces a
# choice: `"s" in "us 9"` is True and so is `"l" in "xl"`, so a plain substring
# test returns shoes when someone asked for a small top.

_STOPWORDS = {
    "the", "a", "an", "in", "for", "with", "and", "under", "size", "looking",
}

# Sizes sort into four families and only match inside their own, with one
# exception — a one-size listing also matches any letter query, because it fits.
_WAIST = re.compile(r"^w\d+")
_DIGITS = re.compile(r"[^\d.]")


def _size_family(size: str) -> str:
    """Which of the four size systems this string belongs to."""
    size = size.lower().strip()
    if "one size" in size:
        return "one"
    if size.startswith("us "):
        return "shoe"
    if _WAIST.match(size):
        return "waist"
    return "letter"


def _size_tokens(size: str) -> set[str]:
    """
    Split a size into whole tokens, dropping any parenthetical.

    "XL (oversized)" → {"xl"} and "S/M" → {"s", "m"}, so matching on token
    equality gives "M" matches "S/M" while "L" does not match "XL".
    """
    size = re.sub(r"\(.*?\)", " ", size.lower())
    return {token for token in re.split(r"[/\s]+", size) if token}


def _size_matches(query_size: str | None, listing_size: str) -> bool:
    """True when a listing's size satisfies the size the user asked for."""
    if not query_size:
        return True

    query_family = _size_family(query_size)
    listing_family = _size_family(listing_size)

    if listing_family == "one" and query_family == "letter":
        return True
    if query_family != listing_family:
        return False

    if query_family == "shoe":
        # US 8 and US 8.5 are different shoes, so compare the numbers.
        try:
            return float(_DIGITS.sub("", query_size)) == float(
                _DIGITS.sub("", listing_size)
            )
        except ValueError:
            return False

    return bool(_size_tokens(query_size) & _size_tokens(listing_size))


def _keywords(description: str) -> list[str]:
    """The words from a description worth scoring on."""
    return [
        word
        for word in re.findall(r"[a-z0-9]+", (description or "").lower())
        if len(word) >= 3 and word not in _STOPWORDS
    ]


def _haystack(listing: dict) -> str:
    """
    The text a keyword is scored against: title, style tags and category.

    Deliberately not `description`. Searching it makes lst_011 and lst_017
    match "tee" when neither is a tee — the free text mentions one in passing.
    """
    return " ".join(
        [listing["title"], " ".join(listing["style_tags"]), listing["category"]]
    ).lower()


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Matched by family and whole token — see _size_matches.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first, ties broken by the
        lower price, capped at config.SEARCH_RESULT_LIMIT.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** The loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Test it from a terminal:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    survivors = [
        listing
        for listing in load_listings()
        if (max_price is None or listing["price"] <= max_price)
        and _size_matches(size, listing["size"])
    ]

    keywords = _keywords(description)

    # "size M under $30" parses to an empty description. Scoring it would give
    # every listing zero and return [], which reads to the loop as "nothing
    # matches" when the filters actually had plenty. Skip scoring instead.
    if not keywords:
        survivors.sort(key=lambda listing: listing["price"])
        return survivors[: config.SEARCH_RESULT_LIMIT]

    scored = []
    for listing in survivors:
        haystack = _haystack(listing)
        score = sum(1 for keyword in keywords if keyword in haystack)
        if score:
            scored.append((score, listing))

    scored.sort(key=lambda pair: (-pair[0], pair[1]["price"]))
    return [listing for _, listing in scored[: config.SEARCH_RESULT_LIMIT]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def _describe_item(item: dict) -> str:
    """One line of item detail for a prompt. Handles brand being None."""
    brand = item.get("brand") or "no brand listed"
    return (
        f"{item['title']} — {item['category']}, size {item['size']}, "
        f"{item['condition']} condition, ${item['price']} on {item['platform']}. "
        f"Brand: {brand}. Colors: {', '.join(item['colors'])}. "
        f"Style: {', '.join(item['style_tags'])}."
    )


def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handled below.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, returns general styling advice for the piece
        itself rather than raising or returning "" — same type, different
        content, because the loop does not branch here.

    Test it from a terminal:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    items = (wardrobe or {}).get("items") or []
    item_details = _describe_item(new_item)

    if not items:
        # The empty-wardrobe path. The user has told us they own nothing, so
        # the one thing the model must not do is invent a closet for them.
        system = (
            "You are a thrift stylist. The user has NOT entered any wardrobe "
            "items, so you do not know what they own. Never refer to a garment "
            "as something they already have, and never say 'your' about a "
            "specific piece. Give general styling direction for the item "
            "itself: what to pair it with, what silhouette it wants, what "
            "occasion it suits. Two short paragraphs at most."
        )
        prompt = (
            f"A shopper is considering this second-hand item:\n\n"
            f"{item_details}\n\n"
            f"They have not set up a wardrobe yet. Give them general styling "
            f"advice for this piece."
        )
    else:
        wardrobe_lines = "\n".join(
            f"- {entry['name']} ({entry['category']}; "
            f"{', '.join(entry['colors'])}; {', '.join(entry['style_tags'])})"
            + (f" — {entry['notes']}" if entry.get("notes") else "")
            for entry in items
        )
        system = (
            "You are a thrift stylist. Suggest outfits built ONLY from the "
            "wardrobe pieces listed, plus the new item. Name each piece exactly "
            "as it is written in the list. Do not invent pieces the user does "
            "not own. Be concrete and brief."
        )
        prompt = (
            f"A shopper is considering this second-hand item:\n\n"
            f"{item_details}\n\n"
            f"Here is everything in their wardrobe:\n\n{wardrobe_lines}\n\n"
            f"Suggest one or two complete outfits pairing the new item with "
            f"pieces they already own. Name the pieces you use."
        )

    suggestion = generate(prompt, system=system).strip()

    # The spec promises a non-empty string. The model is allowed to return "",
    # and the caller should not have to check.
    if not suggestion:
        return (
            f"Couldn't get styling ideas for {new_item['title']} this time — "
            f"try running it again."
        )
    return suggestion


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict, wardrobe: dict | None = None) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.
        wardrobe: the same wardrobe dict suggest_outfit got. **When its items
                  list is empty**, `outfit` is general advice rather than
                  clothes the user owns, and the prompt says so — otherwise a
                  first-person caption writes "over my slip dress" about a slip
                  dress nobody said they had. None keeps the old behaviour.

    Returns:
        A string of two to four sentences, mentioning the item's title, its
        price and its platform once each.
        If `outfit` is empty or whitespace, returns the fixed message
        "No outfit to write about — suggest_outfit returned nothing."
        rather than raising or calling the model.

    It should come out differently for different inputs. If three runs on the
    same item give three identical strings, it's CACHE_ENABLED or TEMPERATURE,
    both near the top of config.py.

    Test it from a terminal:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit or not outfit.strip():
        return "No outfit to write about — suggest_outfit returned nothing."

    system = (
        "You write short captions for second-hand fashion finds, in the voice "
        "of the person who found it. Two to four sentences, no more. Mention "
        "the item, its price and the platform it came from exactly once each. "
        "Be specific about the vibe. Do not write a product description and do "
        "not use bullet points or headings."
    )
    styling_heading = "How it's being styled"

    wardrobe_is_empty = wardrobe is not None and not (wardrobe.get("items") or [])
    if wardrobe_is_empty:
        # Unit 4 fix: in the before run, 2 of 5 empty-wardrobe cards claimed
        # garments ("every pant I own"). The tool had no way to know.
        system += (
            " The person has NOT told us about any clothes they own. The only "
            "garment they have is the find itself. Never write as if they own "
            "or are wearing anything else — no 'my jeans', no 'every pant I "
            "own', no 'I throw it over a slip dress'. Mention pairings only as "
            "ideas, e.g. 'would look great over a slip dress'."
        )
        styling_heading = (
            "General styling ideas (pieces the person does NOT own)"
        )

    prompt = (
        f"The find:\n\n{_describe_item(new_item)}\n\n"
        f"{styling_heading}:\n\n{outfit.strip()}\n\n"
        f"Write the caption."
    )

    return generate(prompt, system=system).strip()
