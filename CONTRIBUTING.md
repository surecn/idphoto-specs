# Contributing

Corrections and additions are welcome. The bar is a source, not an opinion.

## Reporting a wrong spec

Open an issue with:

1. The `countryCode` and `documentId` (for example `JP`, `japan_passport`).
2. The value you believe is correct, with units.
3. **A link to the issuing authority's page** — a government site, consular page or official PDF. Blog posts and photo-studio pages are accepted only as supporting evidence, never as the sole source.

If the authority publishes two conflicting values (it happens), say so and link both. The record will be flagged `needsReview` rather than silently changed.

## Adding a document

1. Add the row to `data/source/items.raw.json` using the same string-encoded format as the existing rows:

   ```json
   {
     "id": "1900",
     "country": "portugal",
     "countryCode": "PT",
     "type": "1",
     "width": "35",
     "height": "45",
     "unit": "1",
     "dpi": "600",
     "bgcolor": "#ffffff",
     "titleResName": "portugal_visa_new"
   }
   ```

   Codes: `unit` is `0` px / `1` mm / `2` in. `type` is `0` passport / `1` visa / `2` driving licence / `3` ID card / `4` other.

2. Add the verified compliance fields only if you have a source: `headMinMm`, `headMaxMm`, `eyeLineMinMm`, `eyeLineMaxMm`, `glassesAllowed`, `expressionStrict`, `expression`, `recencyMonths`.

3. Rebuild and validate:

   ```bash
   python3 scripts/build.py
   python3 scripts/validate.py
   ```

4. Open a pull request. Include the source URL in the description.

A correct row with no compliance fields is more useful than a row with guessed ones. Do not fill in `headMinMm` from a generic ICAO table — several countries deviate, and the whole point of this dataset is that it records the deviations.

## Style

- Sizes as the authority publishes them. Do not convert 2 × 2 in to metric.
- Background colour as lowercase hex.
- `documentId` is `country_snake_case_document`, stable once published.
- One document per record. Variants get their own `documentId` (for example `uk_passport_online` and `uk_passport_offline`).

## Review

Pull requests are checked against the source in the description and then run through `scripts/validate.py` in CI. Changes that contradict an existing `source` field need a newer official source to win.
