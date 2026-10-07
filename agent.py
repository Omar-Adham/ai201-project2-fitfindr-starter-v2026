"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

    python agent.py          runs both example paths below
"""

import re

import config
import trace
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable  # noqa: F401 — unit 4 catches this


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
    }


# ── parsing the query ─────────────────────────────────────────────────────────
#
# Regex, not the model. The parse has to come out the same on every run or
# criterion 2 can't reach 5 of 5, and a model call here would be a third source
# of variance in a loop that already has two.

_PRICE_PATTERNS = (
    re.compile(r"under\s+\$?\s*(\d+(?:\.\d+)?)", re.I),
    re.compile(r"\$\s*(\d+(?:\.\d+)?)"),
)
_SIZE_PATTERNS = (
    re.compile(r"\bsize\s+(US\s*\d+(?:\.\d+)?|[A-Za-z0-9/]+(?:\.\d+)?)", re.I),
    re.compile(r"\b(W\d{2})\b", re.I),
    re.compile(r"\b(US\s*\d+(?:\.\d+)?)\b", re.I),
)


def parse_query(query: str) -> dict:
    """
    Pull a description, a size and a price ceiling out of what the user typed.

    Returns:
        {"description": str, "size": str | None, "max_price": float | None}

    Whatever the price and size patterns consume is cut out of the string, and
    what's left over is the description — so "vintage graphic tee under $30"
    leaves "vintage graphic tee" rather than searching on the word "under".
    """
    leftover = query
    max_price = None
    size = None

    for pattern in _PRICE_PATTERNS:
        match = pattern.search(leftover)
        if match:
            max_price = float(match.group(1))
            leftover = leftover[: match.start()] + " " + leftover[match.end():]
            break

    for pattern in _SIZE_PATTERNS:
        match = pattern.search(leftover)
        if match:
            size = match.group(1).strip()
            size = re.sub(r"^US\s*", "US ", size, flags=re.I)
            # "size 8" means a shoe. Left as a bare "8" it would be read as a
            # letter size and match nothing — see _size_family in tools.py.
            if size.isdigit() or re.fullmatch(r"\d+\.\d+", size):
                size = f"US {size}"
            leftover = leftover[: match.start()] + " " + leftover[match.end():]
            break

    return {
        "description": " ".join(leftover.split()),
        "size": size,
        "max_price": max_price,
    }


def _no_results_message(parsed: dict) -> str:
    """
    Say what the user could change, by working out which filter emptied the list.

    "No results" tells someone nothing. search_listings costs no model call, so
    the loop can afford to re-run it with one constraint relaxed at a time and
    report back whichever relaxation would actually have found something.
    """
    description = parsed["description"]
    size = parsed["size"]
    max_price = parsed["max_price"]

    options = []

    if max_price is not None:
        without_price = search_listings(description, size, None)
        if without_price:
            cheapest = min(item["price"] for item in without_price)
            options.append(
                f"raise your ${max_price:.0f} limit — the closest match is "
                f"${cheapest:.0f}"
            )

    if size:
        without_size = search_listings(description, None, max_price)
        if without_size:
            options.append(
                f"drop the size — nothing in '{size}' matches, but "
                f"{len(without_size)} listing(s) match without that size filter"
            )

    if not search_listings(description, None, None):
        options.append(
            f"try different words — nothing in the catalogue matches "
            f"'{description}'"
        )

    asked_for = f"'{description}'"
    if size:
        asked_for += f" in size {size}"
    if max_price is not None:
        asked_for += f" under ${max_price:.0f}"

    if not options:
        return (
            f"Nothing matched {asked_for}. Try loosening one of the three — "
            f"the words, the size, or the price."
        )

    return f"Nothing matched {asked_for}. You could " + ", or ".join(options) + "."


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    The branch rule, from the README:

        If search_listings returns an empty list, write a message into
        session["error"] naming which constraint to loosen and return the
        session immediately, leaving selected_item, outfit_suggestion and
        fit_card as None. Otherwise take search_results[0], put it in
        session["selected_item"], and go on to suggest_outfit.

    Every value a tool returns is written into the session and read back out of
    the session for the next call — nothing is passed hand to hand.

    IN UNIT 4 this gets trace.step() calls and a ModelUnavailable handler.
    """
    session = new_session(query, wardrobe)

    step = "parse"
    iterations = 0

    while step != "done":
        iterations += 1
        trace.check_iterations(iterations)

        if step == "parse":
            session["parsed"] = parse_query(session["query"])
            step = "search"

        elif step == "search":
            parsed = session["parsed"]
            session["search_results"] = search_listings(
                parsed["description"],
                size=parsed["size"],
                max_price=parsed["max_price"],
            )
            # ── THE BRANCH ──────────────────────────────────────────────────
            # Read the last result back out of the session and let it pick the
            # next step. Empty means stop; anything else means carry on.
            step = "select" if session["search_results"] else "stop"

        elif step == "stop":
            session["error"] = _no_results_message(session["parsed"])
            step = "done"

        elif step == "select":
            session["selected_item"] = session["search_results"][0]
            step = "outfit"

        elif step == "outfit":
            session["outfit_suggestion"] = suggest_outfit(
                session["selected_item"], session["wardrobe"]
            )
            step = "card"

        elif step == "card":
            session["fit_card"] = create_fit_card(
                session["outfit_suggestion"], session["selected_item"]
            )
            step = "done"

        else:  # pragma: no cover — a step name that isn't handled
            raise RuntimeError(f"Unknown step {step!r} in run_agent.")

    return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
