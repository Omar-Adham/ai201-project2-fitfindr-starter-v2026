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
  - `wardrobe` (`dict | None`, default `None`, *added in unit 4*) — the same
    wardrobe dict that went into `suggest_outfit`. When its `"items"` is `[]`,
    the prompt treats `outfit` as general ideas the user doesn't own, so the
    caption never claims other garments. `None` keeps the original behaviour.
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

**Unit 4, Moment 1: a diagnosis that was a guess**

- *What I asked for:* I gave Claude Code the Milestone 2 instructions. Among
  other things, it triggered the model-unavailable failure on a new query,
  `black leather jacket under $70`.
- *What came back:* The search returned a leather belt. Its first explanation
  ("keyword scoring counts 'leather' and 'black' equally") was written before
  it had looked at the data. When it checked the scores, every one of the 10
  results matched exactly 1 of 3 keywords. The real fit, the $75 "90s Leather
  Bomber", was over the limit and doesn't say "jacket".
- *What I changed:* The README now has the explanation that matches the scores,
  not the plausible-sounding one. That changed the conclusion: the problem
  isn't how keywords are weighted, it's that a 1-of-3 match counts as a hit,
  so the empty-search branch never gets the chance to say "raise your limit".
  It's item 1 under What's Still Broken.

**Unit 4, Moment 2: a criterion that passed the thing it was written to catch**

- *What I asked for:* After the before run, I asked for each criterion to be
  read plainly against its target.
- *What came back:* All five were MET. But reading the empty-wardrobe fit cards
  instead of only the outfit text turned up "every high-waisted pant I own" and
  "when I throw it over a slip dress". Criterion 5 passed them because it only
  checked the outfit suggestion.
- *What I changed:* I added a revision under criterion 5 in `criteria.md`
  (original kept), re-scored the same five tries (MISSED 3/5), and traced the
  cause to `create_fit_card` never receiving the wardrobe. That became the one
  improvement, and it took the revised criterion to 5/5. In the same pass,
  Claude's first draft of the criterion-1 reasoning claimed both model tools
  fall back when the model returns an empty reply. I checked `tools.py`: only
  `suggest_outfit` does. The corrected version is item 4 under What's Still
  Broken.

Submission repository: [Omar-Adham/ai201-project2-fitfindr-starter-v2026](https://github.com/Omar-Adham/ai201-project2-fitfindr-starter-v2026).
Keep this same repository for the next unit. See [SUBMISSION.md](SUBMISSION.md)
for the checklist and URL to paste into the course submission form.

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

Produced by `python run_eval.py --label before` (`run_eval.py::main`). Cache was
off and temperature was 0.9. 40 model calls, 11,352 prompt + 3,715 output tokens.
The full output is in [`results/run_2026-10-14_1224_before.md`](results/run_2026-10-14_1224_before.md).
Each criterion has its own scenario in `scenarios.py`, so criteria 1, 3 and 4 are
three separate sets of five runs of the same query, not one run scored three ways.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Impossible query stops before `suggest_outfit` | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Same item at `select`, `suggest_outfit`, `create_fit_card` | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card: price, platform, ≤4 sentences, fresh opening | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Empty wardrobe completes, never claims ownership | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

How each try was scored:
1. `session["error"]` is `None` and `fit_card` is non-empty. All five tries
   completed, with fit cards of 371, 259, 320, 340 and 305 chars.
2. The trace stops at step 3 (`stop`) with no `suggest_outfit` line, and the
   message names something to change.
3. The `select` line, both `new_item=` trace inputs and the run log's
   `selected_item` line all read `Y2K Baby Tee — Butterfly Print ($18.0, depop)`.
4. Each card was checked for: the price as a numeral (`18`), the word `depop`,
   four sentences or fewer, and a first sentence that matches no earlier try's.
   All five had 3 sentences and five different openings.
5. `session["error"]` is `None` and `fit_card` is non-empty, and no sentence in
   the outfit suggestion uses "your", "you own", "you have" or "already" about a
   garment. I also read each one through by hand.

**Real output from one try of each criterion.** The loop is `agent.py::run_agent`,
the tools are in `tools.py`, and the run log is written by
`run_eval.py::write_report`.

Criterion 1, try 1. Fit card from `tools.py::create_fit_card`:

```
- stopped early: no
- selected_item: Y2K Baby Tee — Butterfly Print ($18.0, depop)
- search_results: 10

Fit card:
Scored this dreamy little butterfly baby tee for just $18.0 on Depop and I am
officially living my ultimate 2000s pop star fantasy. The pink and purple
graphic print gives off major early-2000s mall-rat energy, especially when paired
with baggy dark wash denim and chunky kicks. It’s giving nostalgic, low-effort
cool and I'll probably be wearing it on repeat all summer.
```

Criterion 2, try 1. Trace from `agent.py::run_agent`, message from
`agent.py::_no_results_message`:

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

Criterion 3, try 1. Trace from `agent.py::run_agent`:

```
[3] select
      in:  search_results[0]
      out: Y2K Baby Tee — Butterfly Print ($18.0, depop)
[4] suggest_outfit
      in:  new_item=Y2K Baby Tee — Butterfly Print ($18.0, depop), wardrobe=10 items
      out: **Outfit 1: Y2K Streetwear** * New Item: Y2K Baby Tee — Butterfly Print * Baggy straight-leg jeans, dark wash …
[5] create_fit_card
      in:  outfit=<364 chars from suggest_outfit>, new_item=Y2K Baby Tee — Butterfly Print ($18.0, depop)
      out: Scored this dreamy little butterfly print baby tee for just $18.0 on depop and I'm obsessed with the early 200…
```

Criterion 4, try 1. Fit card from `tools.py::create_fit_card`:

```
Scored this buttery soft butterfly baby tee on Depop for just $18.0, and it's
giving major early 2000s mall rat energy. I'm obsessed with throwing it on with
baggy dark denim and a beat-up leather jacket for that effortless off-duty look.
Such a sweet little nostalgic piece for the rotation.
```

Criterion 5, try 2. Outfit from `tools.py::suggest_outfit` (empty-wardrobe
branch) and fit card from `tools.py::create_fit_card`:

```
Outfit suggestion:
This vintage Wrangler cropped denim jacket is a timeless streetwear staple that
balances rugged Americana with a sharp, modern silhouette. Because of its shorter
hemline, it naturally flatters high-waisted bottoms, making it ideal for pairing
with wide-leg trousers, pleated midi skirts, or classic cargo pants to create a
balanced, proportioned look.

It is a versatile piece that easily transitions from casual daytime errands to
weekend outings. Layer it over a slip dress and chunky boots for an effortless
contrast of textures, or wear it buttoned up over a simple baby tee with
distressed denim for a classic Canadian tuxedo.

Fit card:
Scored this cropped Wrangler denim jacket on Poshmark for just $42.0 and I'm
honestly obsessed with the light wash. It gives off the ultimate effortless 90s
streetwear vibe when I throw it over a slip dress and chunky boots. Such a good
find for transitional weather.
```

**Things the criteria passed that I'm still unhappy about** (for Milestone 4):
- **Criterion 4's "fresh opening" check is weak.** All five openings are
  different sentences, but four of the five follow one template: "Scored /
  Scooped this … on Depop for just $18.0 …". Comparing exact sentences counts
  "Scored this little butterfly…" and "Scored this pastel butterfly…" as
  different.
- **Criterion 5 only checks the outfit, and the fit card is where ownership
  creeps in.** In try 4 the card says "goes with literally every high-waisted
  pant **I own**". The criterion as written passes it, because the outfit
  suggestion itself never claimed anything.
- **Every card prints the price as `$18.0` / `$42.0`.** `_describe_item` passes
  the raw float to the prompt, and the model copies it as written.

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
| 1 | Matching query completes all three tools | 4 of 5 | **MET (5/5)** | All five tries had `session["error"] = None` and a non-empty `fit_card` (259–371 chars). |
| 2 | Impossible query stops before `suggest_outfit` | 5 of 5 | **MET (5/5)** | All five traces end at step 3 (`stop`) with no `suggest_outfit` line, and the message names something to change ("try different words"). That is the right advice: dropping the size or the price would still find nothing, and `_no_results_message` re-ran both to confirm it. |
| 3 | Same item at `select`, `suggest_outfit`, `create_fit_card` | 5 of 5 | **MET (5/5)** | In all five tries, all three trace lines and the run log's `selected_item` read `Y2K Baby Tee — Butterfly Print ($18.0, depop)`. |
| 4 | Fit card: price, platform, ≤4 sentences, fresh opening | 4 of 5 | **MET (5/5)** | Every card had `18`, `depop`, 3 sentences, and a first sentence matching no earlier try's. Checked with a script and then by reading each card. |
| 5 | Empty wardrobe completes, outfit never claims ownership | 5 of 5 | **MET (5/5)** as written | All five completed, and no outfit suggestion used "your", "you own", "you have" or "already" about a garment. I read each one too. |
| 5r | *Revised 5:* … and neither the outfit **nor the fit card** claims ownership | 5 of 5 | **MISSED (3/5)** | I re-scored the same five tries, with no re-run. Try 2's card: "when **I throw it over** a slip dress and chunky boots". Try 4's card: "every high-waisted pant **I own**". Tries 1, 3 and 5 pair the jacket with clothes impersonally ("looks so good thrown over a simple slip dress"), and those pass. |

All five criteria met their original targets. Criterion 5 met its target only
because it was checking the wrong text. Once revised to check what its own
reason was about, it misses 3/5 against 5 of 5.

**Diagnoses**

**5r — missed 2 of 5. Step: `create_fit_card`. Place: the model's output, caused
by the tool's inputs.** `create_fit_card(outfit, new_item)` has no wardrobe
parameter, so it can't tell an empty-wardrobe run from a full one. Its system
prompt says to write "in the voice of the person who found it", and its user
prompt passes the outfit text in under "How it's being styled". On the empty
branch, that outfit text is general advice ("pair it with high-waisted wide-leg
trousers, slip dresses, chunky boots"). A first-person caption that's told
those are how the item *is being styled* turns them into the writer's own
clothes: "when I throw it over a slip dress", "every pant I own".
`suggest_outfit` did its job, with a separate empty-wardrobe prompt that forbids
exactly this and five clean outputs. The fix belongs in the tool that lost the
information, not in the one that had it. The loop and the session are fine:
`session["wardrobe"]` holds the empty wardrobe the whole time, and
`run_agent` just never passes it to the card step.

It isn't a one-off. The Milestone 2 empty-wardrobe run, with the cache on and
separate from this log, produced "Threw this cropped Wrangler jacket over **my
favorite floral midi**", which is the same mechanism.

**The pattern across everything I'm unhappy about is `create_fit_card`.** The
ownership claims, the templated openings ("Scored this … on Depop for just
$18.0" in 4 of 5 criterion-4 cards) and the `$18.0` price format all come from
that one tool. It is the only tool whose prompt gets neither the wardrobe nor
any instruction about how to write a price. These are one tool's prompt being
under-specified, not three separate problems.

**Were my targets too low?** Partly, yes:
- **Criterion 1 at 4 of 5 is low.** It only checks that the fit card is
  non-empty. With `ModelUnavailable` caught, the only way left to fail is
  `create_fit_card` getting an empty string back from the model. Unlike
  `suggest_outfit`, it has no fallback for that. I justified 4 of 5 by
  temperature, but temperature changes the *words*, not whether a card comes
  back. 5 of 5 would have been honest, and adding the same fallback to
  `create_fit_card` would close the last gap.
- **Criterion 4 is the one I'd tighten.** "Doesn't open with the same sentence
  as an earlier try" passes cards that differ by one adjective, so it can't
  see the template that 4 of 5 cards follow. I'm not revising it, because the
  check *can* be scored. It's just easy, and making a criterion stricter after
  meeting it is a new target, not a fix. The tighter version would be "no two
  of the five cards open with the same first two words". On this run, "Scored
  this" opens 4 of 5, so it would miss.
- Criteria 2 and 3 at 5 of 5 are correct as they are. Both test code with no
  randomness, so anything short of 5 of 5 would be a bug.



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

**After the whole unit:** every search in both 40-call eval runs went through
MCP. Trace step 2 is labelled `search_listings (via MCP)` in all 50 tries, and
nothing behaved differently from the direct call. The empty case still arrives
as `[]`, so the branch fires exactly as before. The only visible cost is time:
each `call_tool` starts a fresh `mcp_server.py` process.


---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:** One change, to one tool's input and prompt.
`create_fit_card(outfit, new_item)` became `create_fit_card(outfit, new_item,
wardrobe=None)`, and `run_agent` now passes it `session["wardrobe"]`. When that
wardrobe's `"items"` is empty, two things in the prompt change:
- The system prompt gains: *"The person has NOT told us about any clothes they
  own. The only garment they have is the find itself. Never write as if they
  own or are wearing anything else — no 'my jeans', no 'every pant I own', no
  'I throw it over a slip dress'. Mention pairings only as ideas, e.g. 'would
  look great over a slip dress'."*
- The user prompt's heading over the outfit text changes from *"How it's being
  styled"* to *"General styling ideas (pieces the person does NOT own)"*.

With a non-empty wardrobe, the prompt is identical to before, so criteria 1, 3
and 4 send the same prompt in both runs. `test_agent.py` was updated to match
the new call: `create_fit_card` is now asserted to receive the session's own
wardrobe object.

I didn't touch the `$18.0` price format or the templated openings. They have
the same root cause, but fixing them too would mean three changes I couldn't
tell apart.

**Which failure it was meant to fix:** Revised criterion 5, which missed 3/5.
The diagnosis was that `create_fit_card` couldn't know the wardrobe was empty,
so its first-person caption turned the general advice into the user's own
clothes ("every high-waisted pant I own", "when I throw it over a slip dress").

### Run Log — After

Produced by `python run_eval.py --label after` (`run_eval.py::main`), with the
same scenarios, cache off and temperature 0.9. 40 model calls, 11,971 prompt +
3,833 output tokens. The full output is in
[`results/run_2026-10-14_1232_after.md`](results/run_2026-10-14_1232_after.md).

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Impossible query stops before `suggest_outfit` | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Same item at `select`, `suggest_outfit`, `create_fit_card` | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card: price, platform, ≤4 sentences, fresh opening | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Empty wardrobe completes, outfit never claims ownership | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5r. *Revised:* … neither outfit nor fit card claims ownership | 5 of 5 | PASS | PASS | PASS | PASS | PASS | **MET (5/5)** |

**Before and after, side by side:**

| Criterion | Target | Before | After |
|---|---|---|---|
| 1 | 4 of 5 | MET (5/5) | MET (5/5) |
| 2 | 5 of 5 | MET (5/5) | MET (5/5) |
| 3 | 5 of 5 | MET (5/5) | MET (5/5) |
| 4 | 4 of 5 | MET (5/5) | MET (5/5) |
| 5 (original) | 5 of 5 | MET (5/5) | MET (5/5) |
| 5r (revised) | 5 of 5 | **MISSED (3/5)** | **MET (5/5)** |

**Did it help, and how do I know:** Yes. Revised criterion 5 went from 3/5 to
5/5, and nothing else moved. All five empty-wardrobe cards now describe
pairings as possibilities, not as clothes the user owns:

```
try 1: It would look incredible thrown over a slip dress or paired with baggy
       cargo pants for weekend wanders.
try 2: ...would look incredible thrown over a slip dress or paired with a crisp
       white button-down. Can't wait to finally have a proper denim jacket in
       the rotation.
try 3: Would look amazing thrown over a pleated midi skirt for weekend farmers
       markets.
try 4: ...would look amazing thrown over a silky slip dress or paired with
       high-rise trousers.
try 5: ...looks incredible paired with high-waisted parachute pants. Honestly, it
       would also look great over a sleek slip skirt for weekend coffee runs.
```

Compare the before run: "goes with literally every high-waisted pant **I own**"
and "when **I throw it over** a slip dress and chunky boots". Try 2's "finally
have a proper denim jacket" is the card admitting the user *didn't* own one,
which is the opposite of the old failure.

How sure am I? 5/5 against a before rate of 3/5 is clear but not conclusive:
2 failures in 5 could come out 0 in 5 by chance about 8% of the time. The
pattern supports the fix more than the count does. Every after card uses
"would look" phrasing, and that phrasing never appeared in the before cards.

It didn't break the full-wardrobe path. On the example wardrobe the cards still
name the user's own pieces ("my favorite beat-up combat boots", which is a real
wardrobe item), because the prompt only changes when the wardrobe is empty.

It didn't fix the template, and wasn't meant to: 3 of 5 criterion-4 cards
still open "Scored this dreamy…".



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->

**No criterion is still missed.** After the improvement all five original
criteria and revised criterion 5 are MET. But meeting them doesn't mean the
agent is right. Here is what's still wrong, roughly in order of how much a real
user would notice, and why I stopped where I did.

1. **Weak matches win the search.** `black leather jacket under $70` returns a
   leather belt. Every result matches 1 of 3 keywords, and the tie goes to the
   lowest price. The one real fit (the $75 "90s Leather Bomber") is over the
   limit and doesn't say "jacket". Because a 1-keyword match counts as a hit,
   the empty-search branch, which would have said "raise your limit to $75",
   never fires.
   *What I'd do:* treat a result that matches fewer than half the keywords as
   no result, so the existing branch and `_no_results_message` take over. Then
   add a criterion for it, e.g. "for 5 queries whose only real match is over
   budget, the agent suggests raising the limit, 5 of 5".
   *Why I stopped:* none of my five criteria tests search *quality*, so there
   was no miss to diagnose here. The improvement milestone allows one change,
   and the diagnosis pointed at `create_fit_card`. This is the one I'd do next.

2. **Fit cards follow a template.** In the after run, 3 of 5 criterion-4 cards
   open "Scored this dreamy…". Criterion 4's "fresh opening" check compares
   whole sentences, so it can't see this. I named it as the criterion I'd
   tighten in Verdicts and Diagnoses.
   *What I'd do:* tighten criterion 4 to "no two of five cards share their
   first two words". That is a stricter new target, not a revision. Then
   change `create_fit_card`'s prompt to stop opening on the purchase ("lead
   with the vibe or the outfit, not the price").
   *Why I stopped:* this is the same tool I just changed. Changing its prompt
   again in the same pass would have made the criterion-5 result impossible to
   attribute.

3. **Prices print as `$18.0`.** `_describe_item` passes the raw float to the
   prompt, and the model copies it. *What I'd do:* format the price as `$18` /
   `$18.50` in `_describe_item`. It's a one-line change, but it's still a
   second change to the same prompt, which is why I held it back.

4. **`create_fit_card` has no fallback for an empty model reply**, unlike
   `suggest_outfit`. It never happened in the 40 tries that reached the card step (criteria
   1, 3, 4 and 5, five tries each, before and after). If it did, it would pass
   an empty card that criterion 1 would count as a FAIL.
   *What I'd do:* return a fixed message like `suggest_outfit` does.
   *Why I stopped:* nothing in the runs failed this way, so it isn't backed by
   a diagnosis.

5. **The model-down message talks to the developer.** It says "Check
   GEMINI_API_KEY in your .env file". That's actionable for whoever runs the
   app, but a shopper can't act on it. *What I'd do:* split it in two, a
   user-facing line ("styling is down, the listing still stands, try again
   later") and the key/network detail printed only with `--trace`.
   *Why I stopped:* it meets the milestone bar (it names what broke and what to
   do), and choosing the audience is a product decision I haven't made.

6. **Only one call site uses MCP.** `_no_results_message` still calls
   `search_listings` directly for its relax-one-filter re-searches, and every
   `call_tool` starts a new server process. That doesn't matter for
   correctness: direct and MCP results were identical on every query I
   compared. It does matter for speed, which would be the next thing to fix if
   this ever served real traffic, by keeping one session open.

**How solid is the evidence?** Each verdict rests on five tries. That is what
the criteria name, but it's thin for the one change I made: going from 3/5 to
5/5 could come out that way by luck about 8% of the time. A second "after" run
would tighten it. I didn't do one because the milestone asks for one re-run in
the same format, and the complete change in wording ("would look…" in every
after card, never in a before card) is the stronger evidence anyway.



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

       [x] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [x] Run Log — Before, five criteria, five tries each
       [x] Real output pasted underneath, naming file and function
       [x] A verdict on every criterion
       [x] A diagnosis for every miss, naming a place AND a mechanism
       [x] Loop Trace, with the MCP call visible in it
       [x] All three failure modes triggered and handled
       [x] One improvement, with Run Log — After in the same format
       [x] What's Still Broken
       [x] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
