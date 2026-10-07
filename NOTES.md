# Data notes — Milestone 1

Read from `data/listings.json` (40 listings) and `data/wardrobe_schema.json`.
These are the fields `search_listings` can filter on. Anything not listed here
does not exist in the data.

## Listing fields

| Field | Type | Example | Notes for filtering |
|---|---|---|---|
| `id` | str | `lst_001` | `lst_001`–`lst_040` |
| `title` | str | `Vintage Levi's 501 Jeans — Medium Wash` | free text, em-dash separated |
| `description` | str | `Classic 501s in a perfect medium wash...` | free text |
| `category` | str | `bottoms` | closed set, see below |
| `style_tags` | list[str] | `['vintage', 'classic', 'denim', 'streetwear']` | 45 distinct tags |
| `size` | str | `W30 L30` | **not** a closed set — see below |
| `condition` | str | `good` | `good` / `excellent` / `fair` only |
| `price` | float | `38.0` | range 12.0 – 75.0 |
| `colors` | list[str] | `['blue', 'indigo']` | 38 distinct, overlapping names |
| `brand` | str or **None** | `Levi's` | **32 of 40 are None** |
| `platform` | str | `depop` | `depop` 18 / `thredUp` 11 / `poshmark` 11 |

## Things that will bite the search tool

- **`brand` is None most of the time.** 32 of 40 listings have no brand. A
  filter that does `listing['brand'].lower()` crashes on the majority of the
  data. Guard it.
- **`size` is not normalized.** 22 distinct values across 40 listings:
  `M`, `S/M`, `M/L`, `L/XL`, `XL (oversized)`, `XL (fits oversized)`,
  `W27`–`W32`, `W30 L30`, `US 7`–`US 9`, `One Size`, `One Size (adjustable)`,
  `One Size / Oversized`. An exact `==` match on `"M"` finds 8 of the 14 a
  person would call medium (`M` 8, `S/M` 3, `M/L` 3). Substring matching is the
  cheap fix, but note `"S"` is a substring of `"S/M"`, `"US 7"` and `"US 8"`.
- **`colors` names overlap without matching.** `blue` / `light blue` /
  `dark blue` / `medium blue` / `navy` / `indigo` are six separate strings.
  Same for `white` / `off-white` / `ivory` / `cream` / `ecru` / `natural`.
- **`category` is the one genuinely clean closed set:**
  `tops` 15, `bottoms` 10, `outerwear` 8, `shoes` 4, `accessories` 3.
- **Style tags are long-tailed.** `vintage` 29, `classic` 16, `streetwear` 15,
  `earth tones` 11, `cottagecore` 9, `grunge` 8, `90s` 8, `y2k` 7 — then a
  long tail of tags appearing once or twice (`graphic tee` only 3).
- **Decide which fields the search reads, and write it in the Tool Inventory.**
  For "graphic tee", tags and titles happen to agree exactly — `lst_002`,
  `lst_006`, `lst_033`. Adding `description` to the search pulls in `lst_011`
  and `lst_017`, which only *mention* a tee and aren't tees. Wider isn't better.

## Expected result for the demo query

`'vintage graphic tee under $30'` should return exactly three listings. All
three carry both `vintage` and `graphic tee` tags and all are under $30:

| id | title | price |
|---|---|---|
| `lst_002` | Y2K Baby Tee — Butterfly Print | 18.0 |
| `lst_006` | Graphic Tee — 2003 Tour Bootleg Style | 24.0 |
| `lst_033` | Vintage Band Tee — Faded Grey | 19.0 |

If the tool returns more or fewer than these three, the filter is wrong — not
the data.

## Wardrobe shape (what `suggest_outfit` receives)

```json
{ "items": [
  { "id": "w_001",
    "name": "Baggy straight-leg jeans, dark wash",
    "category": "bottoms",
    "colors": ["dark blue", "indigo"],
    "style_tags": ["denim", "streetwear", "baggy"],
    "notes": "High-waisted, sits above the hip" }
] }
```

- Categories: `tops`, `bottoms`, `outerwear`, `shoes`, `accessories`.
- `notes` is optional and **is explicitly `null`** on several example items —
  not missing, present and null. Don't assume a string.
- No `price`, `size`, `condition`, or `brand` on a wardrobe item. The wardrobe
  and a listing do **not** share a shape; only `category`, `colors` and
  `style_tags` line up.
- **Empty wardrobe is `{"items": []}`** — the key exists, the list is empty.
  That's the no-wardrobe branch `suggest_outfit` has to handle.

## Starting position confirmed

```
$ python test.py
10 passed, 0 failed, 0 to look at, 0 skipped

$ python app.py ask 'vintage graphic tee under $30'
  The planning loop isn't built yet — see the TODO in agent.py.

0 model calls this session
```
