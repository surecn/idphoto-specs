# Changelog

## 1.0.0 — 2026-10-17

First public release.

- 724 documents covering 164 countries and territories.
- Split from the app's internal export (781 rows). 50 duplicate groups were merged; the surviving record prefers a millimetre size and the most complete compliance field set.
- 194 records carry chin-to-crown head height, 23 carry eye-line limits, 35 carry a glasses rule, 41 carry a photo-age limit.
- 43 records are flagged `needsReview` where sources disagree on the size; every candidate is listed in `data/quality-report.json`.
- Netherlands corrected to the national 26–30 mm face length for passports, ID cards and driving licences, with the government.nl source attached. The raw export used the Schengen 32–36 mm baseline.
- Four background colours corrected to plain white (Japan, Saudi Arabia, Turkey, Vietnam) where the export carried light grey.
- Thailand passport added: 35 x 45 mm, white background, head 32-36 mm.
- Indonesia passport flagged for review: the export carries a 51 x 51 mm size that looks like a rounded 2 x 2 in.
- Country codes normalised to uppercase. Two source errors fixed: `belgium_driving_license` was exported with the Belarus code, `brazil_driving_license` with the Belgian code.
- Ships `data/specs.json`, `data/specs.csv`, per-country files, a JSON Schema, a build script and a validator.
