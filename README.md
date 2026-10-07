# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->



---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Filters the 40 listings in `data/listings.json` down to the
  ones that fit the shopper's price ceiling and size, ranks the survivors by how
  many of their keywords overlap the description, and returns the best matches.
  It is the only one of the three that never calls the model.
- **Inputs:**
  - `description` (`str`, required) — keywords, e.g. `"vintage graphic tee"`
  - `size` (`str | None`, default `None`) — e.g. `"M"`, `"W30"`, `"US 8"`; `None` skips size filtering
  - `max_price` (`float | None`, default `None`) — inclusive ceiling; `None` skips price filtering
- **Returns:** A `list[dict]` of whole listing dicts, highest score first, ties
  broken by lower price, capped at `config.SEARCH_RESULT_LIMIT` (10). Each dict
  carries all eleven listing fields: `id` (str), `title` (str), `description`
  (str), `category` (str), `style_tags` (list[str]), `size` (str), `condition`
  (str), `price` (float), `colors` (list[str]), `brand` (**str or None**), and
  `platform` (str). The caller gets the full dict, not a summary, so
  `suggest_outfit` and `create_fit_card` can read any field they need.
- **When it has nothing:** The empty list `[]`. Never `None`, never an
  exception, never a string. The loop branches on `if not results`.

**How a size matches** (decided here because the docstring leaves it to the spec,
and because `"s" in "us 9"` and `"l" in "xl"` are both true):

1. Lowercase the size and delete any parenthetical, so `XL (oversized)` → `xl`.
2. Sort it into one of four families — `shoe` (starts `us `), `waist` (matches
   `^w\d+`), `one-size` (contains `one size`), or `letter` (everything else).
3. A listing matches only inside its own family, with one exception: a
   **one-size listing also matches any letter query**, because it genuinely fits.
4. Within `letter` and `waist`, split the size on `/` and whitespace into tokens
   and match on whole-token equality — so `M` matches `S/M` and `M/L`, `W30`
   matches `W30 L30`, and `L` does **not** match `XL`.
5. Within `shoe`, compare the numbers — `US 8` does not match `US 8.5`.

Checked against the data: `M` → 18 listings, `L` → 12, `W30` → 2, `US 8` → 1.

**How keywords score:** lowercase the description, keep word characters, drop
tokens under 3 characters and a small stopword set (`the`, `a`, `an`, `in`,
`for`, `with`, `and`, `under`, `size`, `looking`). Score = how many surviving
keywords appear anywhere in the listing's **title + `style_tags` + `category`**.
Anything scoring zero is dropped. `description` is deliberately **not** searched:
including it makes `lst_011` and `lst_017` match "tee" when neither is a tee.

If the description leaves **no** keywords after stopword removal — `"size M under
$30"` parses to an empty description — every listing scores zero and the tool
would return `[]`, which reads to the loop as "nothing matches" when the price
and size filters actually had plenty. So: when there are no keywords, skip
scoring and return everything that survived the filters, cheapest first.

### `suggest_outfit`

- **What it does:** Asks the model for one or two concrete outfits that pair the
  thrifted item with pieces the user already owns, naming those pieces.
- **Inputs:**
  - `new_item` (`dict`) — one listing dict, exactly as `search_listings` returns it
  - `wardrobe` (`dict`) — has an `"items"` key holding a `list[dict]`; each item
    has `id` (str), `name` (str), `category` (str), `colors` (list[str]),
    `style_tags` (list[str]), `notes` (**str or None**)
- **Returns:** A non-empty `str` — one or two outfit suggestions in prose, each
  naming the wardrobe pieces it uses by their `name` field, so that
  `create_fit_card` has something specific to write about.
- **When it has nothing:** When `wardrobe["items"]` is `[]`, it returns general
  styling advice for the item as a non-empty `str` — same type, different
  content. It does not raise and does not return `""`, because the loop does not
  branch here; it carries on to `create_fit_card` either way.

### `create_fit_card`

- **What it does:** Writes a short caption someone would actually post about the
  find, in the voice of a person rather than a product listing.
- **Inputs:**
  - `outfit` (`str`) — the string `suggest_outfit` returned
  - `new_item` (`dict`) — the same listing dict that went into `suggest_outfit`
- **Returns:** A `str` of two to four sentences that mentions the item's `title`,
  its `price`, and its `platform` once each, and that differs between runs
  (`TEMPERATURE` is 0.9 and the eval harness disables the cache).
- **When it has nothing:** When `outfit` is empty or whitespace-only, it returns
  the fixed string `"No outfit to write about — suggest_outfit returned
  nothing."` rather than raising or calling the model. A `str` either way, so the
  caller never type-checks the result.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, write a message into
`session["error"]` naming which constraint to loosen — the price ceiling, the
size, or the keywords — and return the session immediately, leaving
`selected_item`, `outfit_suggestion` and `fit_card` as `None`. Otherwise take
`search_results[0]`, put it in `session["selected_item"]`, and go on to
`suggest_outfit`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** Regex, not the model — the parse has to be the same
every run or criterion 2 can't hit 5 of 5, and a model call here would be a third
source of variance in a loop that already has two.

- `max_price` — `under \$?(\d+)` or `\$(\d+)`, cast to `float`
- `size` — `\bsize\s+([a-z0-9/.]+)\b`, or a bare `W\d+` / `US \d+(\.\d+)?`
- `description` — the query with those matched spans removed, then stopwords dropped

**What moves through the session:** In this order —

1. `query` — the raw string the user typed
2. `parsed` — `{"description": str, "size": str | None, "max_price": float | None}`
3. `search_results` — the `list[dict]` from `search_listings` (possibly `[]`)
4. **branch** — `[]` sets `error` and returns; anything else continues
5. `selected_item` — `search_results[0]`, the whole listing dict
6. `outfit_suggestion` — the `str` from `suggest_outfit(selected_item, wardrobe)`
7. `fit_card` — the `str` from `create_fit_card(outfit_suggestion, selected_item)`

`selected_item` is the same dict object that `search_listings` returned and the
same one both model tools receive — that identity is what criterion 3 checks.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask '...'

```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"

```

```
$ python -c "from tools import suggest_outfit; ..."

```

```
$ python -c "from tools import create_fit_card; ..."

```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:*
- *What came back:*
- *What I changed:*

**Moment 2**

- *What I asked for:*
- *What came back:*
- *What I changed:*

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
