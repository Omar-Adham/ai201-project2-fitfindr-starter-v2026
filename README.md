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
> The three tools and planning loop are implemented. Matching queries need
> access to the configured model; an impossible query stops without a model call.
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

FitFindr is a command-line thrift styling agent: a shopper can ask for something
like `vintage graphic tee under $30`, optionally specifying a size. It searches
40 mock second-hand listings, chooses the highest-ranked match, and asks Gemini
for outfit suggestions using the example wardrobe, or general styling advice
when the wardrobe is empty. It then writes a short fit-card caption about the
find, including its price and platform. If nothing matches, it stops before
either model tool and suggests changing the keywords, size, or price ceiling.


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

- `max_price` — an amount after `under` (optional `$`) or after `$`, including
  decimals, cast to `float`
- `size` — a value after `size`, or a bare waist/shoe size such as `W30` or
  `US 8`; `size 8`, `size US 8`, and `US8` normalize to `US 8`
- `description` — the query with those matched spans removed and whitespace normalized;
  `search_listings` drops stopwords when scoring it

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

Milestone 5 verification (2026-10-07): the live run completed all three tools
and returned a fit card. The initial run made two model calls (626 prompt and
196 output tokens). The repeat below reused those real responses from cache
while checking the actual inputs received by both model tools.

```
$ python app.py ask 'vintage graphic tee under $30'
Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Here are two complete outfits using the new Y2K Baby Tee — Butterfly Print and pieces from your wardrobe:

**Outfit 1: Y2K Streetwear**
*   Y2K Baby Tee — Butterfly Print
*   Baggy straight-leg jeans, dark wash
*   Chunky white sneakers
*   Black crossbody bag

**Outfit 2: Casual Layered Grunge**
*   Y2K Baby Tee — Butterfly Print
*   Wide-leg khaki trousers
*   Black cropped zip hoodie
*   Black combat boots

  Fit card: Scored this little butterfly print baby tee on Depop for just $18.0 and I'm instantly transported back to 2003. It's giving major early-2000s mall rat energy, especially paired with baggy dark-wash denim and chunky kicks. Can't wait to grunge it down with combat boots and an oversized zip-up for my next coffee run.

0 model calls this session, 2 served from cache
```

The impossible query completed using the real search tool:

```
$ python app.py ask 'designer ballgown size XXS under $5'
  Nothing matched 'designer ballgown' in size XXS under $5. You could try different words — nothing in the catalogue matches 'designer ballgown'.

0 model calls this session
```

State and branch checks run without network access:

```
$ python -m unittest test_agent -v
Ran 5 tests
OK
```

These checks use real search results and mock the two model tools. They verify
the selected item is already in the session when each tool receives it, that
the saved outfit reaches the card tool, that an empty wardrobe proceeds, and
that the impossible query skips both model tools in five tries. They also
check shoe-size parsing and actionable price advice. They do not evaluate
generated caption quality or replace the later five-trial model evaluation.

The full happy-path session (real model responses, reused from cache) and
empty-search session are in [results/milestone5_sessions.txt](results/milestone5_sessions.txt).
Both model tools received the same selected item object. On the empty branch,
`selected_item`, `outfit_suggestion`, and `fit_card` remained `None`.

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
[{'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute
early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits
like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee',
'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white',
'pink', 'purple'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_033', 'title': 'Vintage
Band Tee — Faded Grey', ...]

4 results, whole listing dicts, best match first: lst_002 ($18), lst_033 ($19),
lst_006 ($24), lst_015 ($26). Every price is at or under the $30 ceiling.
```

```
$ python -c "from tools import search_listings; print(search_listings('designer ballgown', size='XXS', max_price=5))"
[]
```
The empty case, as specced — an empty list, not `None` and not a crash. This is
what the loop branches on.

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
Here is an outfit using the Vintage Levi's 501 Jeans:

**Outfit 1: Classic Streetwear**
*   Vintage Levi's 501 Jeans — Medium Wash
*   White ribbed tank top
*   Vintage black denim jacket
*   Chunky white sneakers
*   Black crossbody bag
```
Every piece after the jeans is a real wardrobe entry, named exactly as
`wardrobe_schema.json` writes it — it isn't inventing a closet.

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_empty_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_empty_wardrobe()))"
Vintage Levi's 501s in a medium wash are the ultimate canvas for a timeless, effortless
wardrobe. With a classic straight-leg cut and rigid denim structure, these bottoms
naturally call for balance—think fitted baby tees, cropped cardigans, or a tucked-in
oversized button-down to define the waist. [...]
```
The empty-wardrobe case: general styling advice, still a non-empty string, and it
never claims the user owns anything. That's criterion 5's condition.

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
Finally found the holy grail of slouchy denim that actually holds you in at the waist.
Scored these vintage Levi's 501 jeans on depop for just $38.0 and they are already my new
absolute favorite. Threw them on with crisp white sneakers for that effortlessly cool,
lived-in 90s streetwear vibe.
```
Three sentences, names the item, the price and the platform once each.

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(repr(create_fit_card('   ', load_listings()[0])))"
'No outfit to write about — suggest_outfit returned nothing.'
```
The empty case: the fixed string from the spec, with no model call made.

**Three runs on the same item**

Run three times with the starter's settings untouched and all three are
word-for-word identical — `CACHE_ENABLED` is `True`, so runs 2 and 3 were served
the answer run 1 had already paid for. Setting `config.CACHE_ENABLED = False`
gives three different cards at `TEMPERATURE = 0.9`:

```
run 1: Scored these vintage Levi's 501 jeans on Depop for just $38.0 and they fit like an
       absolute dream. [...] Perfect downtown uniform unlocked.
run 2: Scored these vintage Levi's 501 jeans on Depop for just $38.00 and they fit like an
       absolute dream. [...] It's the ultimate effortless streetwear uniform [...]
run 3: Finally tracked down these vintage Levi's 501 jeans on Depop and they fit like an
       absolute dream for thirty-eight bucks. [...]
```

Different, but **runs 1 and 2 have nearly identical openings**, differing only
in price formatting (`$38.0` versus `$38.00`), and run 3 writes the price as
"thirty-eight bucks" rather than a numeral. The latter misses criterion 4's
numeric-price condition; the first two are technically distinct openings under
the existing criterion but show limited variation.
Noting it here rather than changing the target.

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:* I gave Codex the milestone instructions and asked it to
  read the project, review my work through milestone 4, and continue milestone 5.
- *What came back:* It found an existing uncommitted planning loop and a parsing
  bug: `size US 8` captured `US` rather than the complete shoe size. It also
  added checks of the actual arguments received by both model tools.
- *What I changed:* With Codex's help, I updated `agent.py::parse_query` to
  capture and normalize the shoe size, preserved the loop's session-based
  handoff, and added `test_agent.py`. The five tests cover state handoff,
  early stopping, empty wardrobes, shoe sizes, and price advice.

**Moment 2**

- *What I asked for:* I asked whether everything through milestone 5 was done,
  then told Codex to finish the remaining verification and commit it.
- *What came back:* It distinguished the passing offline tests from the still
  pending real model run. After I authorized completion, the live Gemini run
  returned a fit card for the $18 butterfly tee; the impossible query stopped
  without calling either model tool.
- *What I changed:* With Codex's help, I replaced the pending-run note in this
  README with actual output and saved both full sessions in
  `results/milestone5_sessions.txt`. The evidence labels the cached repeat
  separately from the live run, and milestone 5 was committed as `d902aa7`.

Submission repository: [Omar-Adham/ai201-project2-fitfindr-starter-v2026](https://github.com/Omar-Adham/ai201-project2-fitfindr-starter-v2026).
Keep this same repository for the next unit. See [SUBMISSION.md](SUBMISSION.md)
for the checklist and URL to paste into the course submission form.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

The sections below are reserved for unit 4 and are intentionally unfinished
in this unit 3 submission.

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

**Happy path** — `python app.py ask 'vintage graphic tee under $30' --trace`

```
[1] parse_query
      in:  vintage graphic tee under $30
      out: {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
[2] search_listings (via MCP)
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
      out: 10 items: Y2K Baby Tee — Butterfly Print, Vintage Band Tee — Faded Grey, Graphic Tee — 2003 Tour Bootleg Style … +7 more
      →    branch: results, continuing
[3] select
      in:  search_results[0]
      out: Y2K Baby Tee — Butterfly Print ($18.0, depop)
[4] suggest_outfit
      in:  new_item='Y2K Baby Tee — Butterfly Print', wardrobe=10 items
      out: Here are two complete outfits using the new Y2K Baby Tee — Butterfly Print and pieces from your wardrobe:  **O…
[5] create_fit_card
      in:  outfit=<412 chars from suggest_outfit>, new_item='Y2K Baby Tee — Butterfly Print'
      out: Scored this little butterfly print baby tee on Depop for just $18.0 and I'm instantly transported back to 2003…
```

**Empty search** — `python app.py ask 'designer ballgown size XXS under $5' --trace`

```
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
[2] search_listings (via MCP)
      in:  {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
      out: [] (empty)
      →    branch: empty, stopping
[3] stop
      out: Nothing matched 'designer ballgown' in size XXS under $5. You could try different words — nothing in the catal…
      →    no model calls made
```

Three steps instead of five, and no model calls: the branch is what stops it.

**Failure modes, triggered on purpose**

| Failure | How I triggered it | What the agent said | Handler needed? |
|---|---|---|---|
| Empty search | `ask 'designer ballgown size XXS under $5'` | "Nothing matched 'designer ballgown' in size XXS under $5. You could try different words — nothing in the catalogue matches 'designer ballgown'." | No. The branch already stops with a message that says what to change. |
| Empty wardrobe | `ask 'denim jacket under $50' --empty-wardrobe` | General styling advice for the light-wash cropped denim jacket (pair it with high-waisted pieces, a floral midi dress, wide-leg trousers), then a fit card. Not a crash, not `""`. | No. `suggest_outfit` already has an empty-wardrobe prompt. |
| Model unavailable | Bad `GEMINI_API_KEY` on a query not yet cached (`ask 'black leather jacket under $70'`) | **Before:** `ModelUnavailable: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.` with exit code 1. The listing the search had already found was thrown away, and interactive `ask` mode would have quit. | **Yes.** |

The fix for the model-unavailable case is in `run_agent()`. It catches
`ModelUnavailable` around `suggest_outfit` and `create_fit_card`, writes a
message into `session["error"]`, and stops, keeping whatever was already found.
After the fix:

> Found Leather Belt — Brown, Braided — $12.00 on thredUp — but couldn't suggest an outfit, because the styling model couldn't be reached. The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com. The listing itself is still valid; the search doesn't need the model.

The message names what broke (the styling model), why (the key, network or
model name, whichever `generate._explain` found), and what still worked (the
listing). I also forced a failure at the fit-card step, which a bad key can't
reach because the outfit step fails first. That run stops at step 5, keeps the
outfit and shows it, and leaves `fit_card` as `None`.

Two things the failure runs turned up for Milestone 4:
- "black leather jacket under $70" returns a *leather belt* first. Every one of
  the 10 results matches exactly 1 of the 3 keywords, so the tie goes to the
  cheapest. The only real fit, "90s Leather Bomber — Black", costs $75 and calls
  itself a bomber, not a jacket. A one-keyword match counts as a hit, so the
  empty-search branch never fires, and the user gets a belt instead of "raise
  your limit to $75".
- With an empty wardrobe, the fit card still says "my favorite floral midi". The
  outfit advice correctly avoids claiming the user owns anything, but the
  caption prompt has no such rule.

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->

`search_listings` is now registered in `mcp_server.py` with the same three typed
inputs as the Tool Inventory (`description: str`, `size: str | None`,
`max_price: float | None`) and a description written for a caller who can't see
the code: units (US dollars, inclusive), the size families, the fields in each
result, and the empty case (`[]`, never null or an error). `python mcp_client.py`
lists it with those three inputs.

In `run_agent()`, the `search` step now calls
`call_tool("search_listings", {...})` instead of importing the function. Nothing
behaved differently afterwards. I compared direct and MCP results on four
queries (a normal match, the empty ballgown search, a size-and-price query with
no keywords, and a `W30` waist size), and all four were equal, including the
empty `[]`. `python agent.py` runs both paths end to end and `test_agent.py`
passes. The one cost is speed: every call starts a fresh server process.

`_no_results_message` still calls `search_listings` directly for its
relax-one-filter re-searches. The milestone moves one call site, and those
re-runs only build the error text.


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
