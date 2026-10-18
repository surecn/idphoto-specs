# Document Photo Specs

**Open dataset of passport, visa and ID photo requirements for 164 countries and territories — 724 documents, machine-readable, no API key required.**

![documents](https://img.shields.io/badge/documents-724-blue)
![countries](https://img.shields.io/badge/countries-164-green)
![license](https://img.shields.io/badge/license-CC%20BY%204.0-lightgrey)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23449086.svg)](https://doi.org/10.5281/zenodo.23449086)

Most photo tools hard-code a handful of sizes. This dataset covers the long tail: national ID cards, residence permits, driving licences, seafarer books, exam registrations and more, each with the print size the issuing authority actually asks for.

Maintained by [IDPhotoWork](https://www.idphotowork.com/) — a free online passport and ID photo maker.

---

## What is inside

| | |
|---|---|
| Documents | **724** |
| Countries and territories | **164** |
| Passport specs | 164 |
| Visa specs | 219 |
| ID card specs | 194 |
| Driving licence specs | 55 |
| Other documents | 92 |
| Records with head-height limits | 194 |
| Records with eye-line limits | 23 |

724 unique documents. The source catalogue held 781 rows; 57 of them were the same document expressed twice (millimetres vs inches vs pixels) and were merged into one record, with the pixel variant kept as `pixelWidth` / `pixelHeight`. The merge log is in `data/quality-report.json`.

Every record carries the print size, the required background colour and the resolution the spec is written for. Where the issuing authority publishes them, the record also carries the chin-to-crown head height, the eye-line position, whether glasses are allowed, whether the neutral-expression rule is legally binding, and the maximum age of the photo.

## Quick start

```bash
curl -s https://raw.githubusercontent.com/surecn/idphoto-specs/main/data/specs.json | jq '.[] | select(.countryCode=="JP" and .documentType=="passport")'
```

```js
const specs = await fetch(
  'https://raw.githubusercontent.com/surecn/idphoto-specs/main/data/specs.json'
).then(r => r.json());

const japan = specs.find(s => s.countryCode === 'JP' && s.documentType === 'passport');
console.log(japan.widthMm, japan.heightMm, japan.headMinMm, japan.headMaxMm);
// 35 45 32 36
```

```python
import json, urllib.request

with urllib.request.urlopen('https://raw.githubusercontent.com/surecn/idphoto-specs/main/data/specs.json') as fh:
    specs = json.load(fh)

us = next(s for s in specs if s['documentId'] == 'us_passport')
print(us['widthMm'], us['heightMm'], us['backgroundColor'])  # 50.8 50.8 #ffffff
```

Need a single country? `data/by-country/JP.json` holds just that country's records.

If `raw.githubusercontent.com` is slow or unreachable from your network, the same files are served by jsDelivr:

```bash
curl -s https://cdn.jsdelivr.net/gh/surecn/idphoto-specs@main/data/specs.json
```

## Data model

One record per document. Physical sizes are in millimetres; pixel sizes are kept separate and never mixed in.

```json
{
  "id": 319,
  "countryCode": "JP",
  "country": "japan",
  "countryName": "Japan",
  "documentType": "passport",
  "documentId": "japan_passport",
  "width": 35,
  "height": 45,
  "unit": "mm",
  "widthMm": 35,
  "heightMm": 45,
  "dpi": 600,
  "backgroundColor": "#eeeeee",
  "headMinMm": 32,
  "headMaxMm": 36,
  "recencyMonths": 6,
  "glassesAllowed": true,
  "expressionStrict": true,
  "expression": "neutral, mouth closed, eyes open",
  "guide": "https://www.idphotowork.com/japan-passport-photo.html"
}
```

| Field | Type | Notes |
|---|---|---|
| `id` | integer | Stable within a release, gap-free |
| `countryCode` | string | ISO 3166-1 alpha-2, uppercase |
| `country` | string | Slug used by the source system |
| `countryName` | string | Display name |
| `documentType` | enum | `passport` · `visa` · `id_card` · `driving_licence` · `other` |
| `documentId` | string | Stable document key, unique with `countryCode` |
| `width`, `height` | number | Expressed in `unit` |
| `unit` | enum | `mm` · `in` · `px` |
| `widthMm`, `heightMm` | number | Derived for `mm` and `in` records, omitted for `px` |
| `pixelWidth`, `pixelHeight` | integer | Only when a digital variant exists |
| `dpi` | integer | Resolution the spec is written for |
| `backgroundColor` | string | Lowercase hex, e.g. `#ffffff` |
| `headMinMm`, `headMaxMm` | number | Chin to crown, omitted when unverified |
| `eyeLineMinMm`, `eyeLineMaxMm` | number | Distance from the bottom edge to the eye line |
| `glassesAllowed` | boolean | Omitted when the rule is not verified |
| `expressionStrict` | boolean | `true` when neutral expression is a hard rule, `false` when it is a preference |
| `expression` | string | Wording from the issuing authority |
| `recencyMonths` | integer | Maximum age of the photo |
| `guide` | uri | Illustrated requirements page on idphotowork.com |
| `source` | uri | Official source, present when a value was corrected or verified |
| `needsReview` | boolean | Size disputed or unconfirmed — treat as provisional |
| `reviewNote` | string | Why the record is flagged |

**A missing field means "not verified", never "no requirement".** Do not treat an omitted `headMinMm` as permission to skip the check. If your application needs a complete rule set, filter on the fields you require:

```js
const complete = specs.filter(s => s.headMinMm != null && s.expressionStrict != null);
```

## Files

```
data/
├── specs.json            All 724 records, one JSON array
├── specs.csv             Same data as flat CSV
├── index.json            Counts and the country index
├── quality-report.json   Merged duplicates and every unresolved size conflict
├── by-country/<CC>.json  One array per country
└── source/items.raw.json Original export, kept for reproducibility
schema/spec.schema.json   JSON Schema (draft-07)
scripts/build.py          Rebuilds every file above from the raw export
scripts/validate.py       Structural and cross-file validation
examples/                 Python and JavaScript snippets
```

## Accuracy

Specifications were collected from issuing authorities and cross-checked against at least two independent sources before being written down. Values that could not be reconciled are not guessed: they are either omitted or flagged `needsReview: true` and listed in `data/quality-report.json` with every candidate value.

There is a known failure mode in this domain that the dataset documents explicitly: several countries deviate from the ICAO baseline. The Netherlands uses a 26–30 mm face length for national documents instead of the Schengen 32–36 mm, Switzerland uses 29–34 mm, and South Africa requires a light grey or cream background rather than white. These records carry a `source` link.

Two limitations to be aware of:

1. **Compliance fields are partial.** Head height is present on 194 of 724 records. The rest specify only size, background and resolution, which is all many authorities publish.
2. **Background colours are rendering targets.** `backgroundColor` is the colour a compliant photo should have, expressed as hex. Where an authority accepts a range (for example light grey or light blue), the record carries the most common choice.

Details on sourcing and on how conflicts are resolved: [docs/methodology.md](docs/methodology.md).

## Licensing and attribution

Data is licensed under [CC BY 4.0](LICENSE). Scripts and examples are MIT. Commercial use is allowed; attribution is required.

```text
Photo specification data from IDPhotoWork (https://www.idphotowork.com/),
licensed under CC BY 4.0. DOI: 10.5281/zenodo.23449086
```

A link back is the only thing we ask in return for the data — it is also what funds keeping the dataset current.

## Contributing

Corrections are welcome, especially with an official source attached. See [CONTRIBUTING.md](CONTRIBUTING.md). If a spec in your country is wrong, open an issue with the link to the government page and it will be fixed.

## Disclaimer

This dataset is a reference implementation, not legal advice. Requirements change without notice, and the issuing authority always has the final say. Verify against the official source before submitting an application.
