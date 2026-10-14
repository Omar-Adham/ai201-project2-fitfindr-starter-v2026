# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
<!-- Why 4 of 5 and not 5 of 5? Something about your search, probably —
     "my search is a plain keyword match and some phrasings will miss" is a
     real answer. -->

Across five tries of the *same* query the search half is deterministic — same
parse, same filters, same ten results every time. So all the variance in this
row lives in the two model calls, and either one can come back with something
that doesn't hold up. 4 of 5 leaves room for one bad generation in five. 5 of 5
would be claiming a sampled model at `TEMPERATURE = 0.9` never has an off run,
and I picked that temperature on purpose.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
<!-- Why is 5 of 5 reasonable here when criterion 1 isn't? What's different
     about this path? -->

This path returns **before** `suggest_outfit`, so it makes zero model calls —
that's the whole difference from criterion 1. Parse, filter and the empty-list
check are all my own deterministic code, so five tries of one query must give
five identical outcomes. A failure here can't be a bad roll; it means the branch
is wrong. Anything short of 5 of 5 would be excusing a bug.

---

## 3. Something about state

<!-- YOU WRITE THIS ONE.

     How would you know that the item your search found is the same item the
     next tool received? Name something countable or observable.

     This is the criterion people find hardest, because state failure doesn't
     look like state failure — it looks like a tool problem. Something that
     compares session["selected_item"] against what actually reached
     suggest_outfit is the shape you're after. -->

On the matching query, the item identity printed three times in one run — the
`selected_item` line in the run log, the `new_item` input on the trace line for
`suggest_outfit`, and the `new_item` input on the trace line for
`create_fit_card` — is the same title, the same price and the same platform in
all three places, in 5 of 5 tries.

**Why this target:**

`trace._short()` renders any dict with a `title` key as `title ($price,
platform)`, so those three lines are directly comparable by eye with no extra
code — that's why the criterion is phrased against title/price/platform and not
against `id`, which the run log never prints.

5 of 5 because nothing between the three points is stochastic. `selected_item`
is assigned once from `search_results[0]` and passed by reference to both model
tools; no model call can alter it. A mismatch would mean my loop re-ran the
search, re-indexed the list, or passed the wrong variable. That's a defect with
one cause, not a roll of the dice, so one failure in five is still a failure.

---

## 4. Something about the fit card

<!-- YOU WRITE THIS ONE.

     The fit card calls a model, so the same input can produce different words
     each time. That's not a bug — it's the nature of the tool. So what would
     make it acceptable?

     Think about what you'd actually be unhappy to see. A caption that never
     mentions the price? Two different items producing the same opening
     sentence? A card longer than a caption anyone would post? Any of those can
     be turned into a number. -->

On the matching query, a try passes when its fit card does all four of these:
contains the item's price as a numeral, contains the platform name, runs to four
sentences or fewer, and does not open with the same sentence as any earlier try
in the run. Target: 4 of 5.

**Why this target:**

The first three are the things I'd actually be unhappy to see — a caption that
makes me go and look up what it cost, one that doesn't say where to buy it, or
one that's a paragraph when a caption is two lines. The fourth is how I turn
"different every time" into something countable: five cards, five distinct
openings, checkable by reading the report.

4 of 5 and not 5 of 5 because all four conditions are the model's to satisfy,
and I set `TEMPERATURE = 0.9` precisely so it wouldn't produce the same card
twice. Demanding all five land every detail is demanding the variance I asked
for not show up. One card in five that runs long or drops the platform is the
cost of captions that don't read like a template.

Not stricter on length: four sentences is already the top of the range
`create_fit_card` is specced for, so a fifth sentence is a real miss rather than
a rounding error.

---

## 5. Your choice

<!-- YOU WRITE THIS ONE TOO.

     Pick something you actually care about getting right. Speed, the empty
     wardrobe path, what happens when the model can't be reached, whether the
     search respects a price ceiling — anything, as long as it names a number
     or an observable outcome. -->

With an **empty** wardrobe and the query `denim jacket under $50`, the agent
still completes all three tools — `session["error"]` is `None` and `fit_card` is
non-empty — and the outfit suggestion never refers to a specific garment as one
the user already owns. 5 of 5 tries.

**Why this target:**

This is the failure mode most likely to reach a real user, because every new
user starts here. An empty wardrobe isn't an error, so the run has to finish
rather than branch out — and the thing that would embarrass me is a suggestion
that confidently pairs the jacket with "your white tee" when the user has told
me they own nothing.

5 of 5 because the branch is my own `if wardrobe["items"]` — deterministic, so
it can't take the wrong path only sometimes. The half that depends on the model
is whether the prompt I send on the empty branch keeps it from inventing a
closet. If the model invents one even once in five, that's my prompt being
loose, not an unlucky sample, and I'd want to fix it rather than score around it.

I chose this over "the search respects the price ceiling", which I also care
about, because the run log records `len(search_results)` but not the prices in
it — scoring that would have meant writing extra checking code, and the
criterion would have been measuring my test harness as much as my agent.

> **Revised in unit 4:** With an **empty** wardrobe and the query `denim jacket
> under $50`, the agent still completes all three tools (`session["error"]` is
> `None` and `fit_card` is non-empty), and **neither the outfit suggestion nor
> the fit card** presents a garment other than the new item as one the user
> owns or wears. That means no "your X", no "my X", no "X I own", and no "I
> pair / throw / wear it with X". 5 of 5 tries.
>
> **Why revised:** The original only looked at the outfit suggestion, so it
> measured the wrong thing. The failure the "why" above names (pairing the
> jacket with clothes the user never said they owned) reaches the user through
> **both** pieces of text, and in the before run it showed up only in the fit
> card. Try 4's card says "goes with literally every high-waisted pant I own",
> and the original criterion passed it, because the outfit suggestion it
> checked was clean. A criterion that can't see the failure it was written to
> catch can't be scored. The target stays at 5 of 5, for the reason already
> given above.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
