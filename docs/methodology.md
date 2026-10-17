# Methodology

How the records in this dataset are produced, and what the flags mean.

## Scope

One record describes the photo required for one specific document: a passport, a visa, a national ID card, a driving licence, or another photo-bearing document such as a residence permit or a professional licence.

A record answers a narrow question: *if I hand in a photo for this document, what must it look like?* It does not describe the application process, the number of copies, or where to submit.

## Collection

For every document the following values are collected, in order of authority:

1. The issuing authority's own publication — a government site, a consular page, an official PDF, or a published photo template.
2. Failing that, two independent secondary sources that agree.

If neither step produces an unambiguous answer, the field is left out. Where two credible sources disagree on a value that matters (usually the head height), the record keeps the value with better provenance and is flagged `needsReview: true`, and both candidates are written to `data/quality-report.json`.

Sizes are recorded as published. A 2 × 2 in specification stays in inches; it is not rounded to 50.8 × 50.8 mm and then re-labelled as metric, because the authority will check against 2 inches.

## Known deviations from the ICAO baseline

The dataset is useful precisely because it does not assume the 35 × 45 mm / 32–36 mm headline. Documented exceptions include:

| Country | Baseline expectation | Actual requirement |
|---|---|---|
| Netherlands | face 32–36 mm | **26–30 mm** for passports, ID cards and driving licences |
| Switzerland | head 32–36 mm | **29–34 mm**, light grey background |
| South Africa | white background | **light grey or cream**, photo under one month old |
| Argentina | 35 × 45 mm | **40 × 40 mm** square |
| Japan | — | 35 × 45 mm portrait (not 45 × 35) |

Every such record carries a `source` field pointing at the official publication.

## Duplicates and conflicts

The source export contained 781 rows, of which 50 groups described the same document twice — usually a metric entry plus a generic 2 × 2 in fallback, or a print size plus a pixel variant.

Handling rules, applied by `scripts/build.py`:

1. Records are grouped by `(countryCode, documentId)`.
2. Within a group the record with a millimetre size wins over inches, which wins over pixels; ties break on the number of verified compliance fields.
3. When both a print and a pixel specification exist, the pixel dimensions are attached to the surviving record as `pixelWidth` / `pixelHeight` rather than kept as a second row.
4. When the surviving record's size disagrees with another candidate by more than rounding, it is flagged `needsReview: true` and the group is written to `data/quality-report.json`.

This is why the published count (723) is lower than the source row count (781).

## Corrections

Corrections that have been verified against an official source are applied in `scripts/build.py` under `CORRECTIONS`, with the source URL recorded on the affected records. This keeps the raw export untouched and every change auditable.

## Versioning

`MAJOR.MINOR.PATCH` for the dataset:

- **MAJOR** — schema change that breaks existing consumers.
- **MINOR** — new records, new countries, new optional fields.
- **PATCH** — corrected values, no structural change.

Record `id`s are stable across PATCH and MINOR releases for records that are not removed. Identify records by `(countryCode, documentId)` if you need a key that survives schema changes.

## What is deliberately excluded

- Requirements that cannot be expressed as a numeric or boolean constraint, such as "no shadows" or "neutral lighting". These live in the prose guide, not in the data.
- Documents whose size could not be confirmed by at least one credible source. A missing record is better than a wrong one.
- Application fees, processing times and submission channels.
