#!/usr/bin/env python3
"""Build the public dataset from the raw app export.

Usage:
    python3 scripts/build.py

Inputs
    data/source/items.raw.json   Raw export (781 rows, string values, internal codes)

Outputs
    data/specs.json              Normalized dataset, one record per document
    data/specs.csv               Same data as CSV
    data/index.json              Country index and counts
    data/by-country/<CC>.json    One file per country
    data/quality-report.json     Merged duplicates and unresolved conflicts

Design rules
    * Unknown means unknown: optional fields are omitted, never zero-filled.
    * Never convert a print size to pixels or the other way around silently.
    * When two rows describe the same document and disagree on the size, the
      record is kept but flagged with "needsReview": true and the alternatives
      are written to quality-report.json.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "source" / "items.raw.json"

UNIT = {"0": "px", "1": "mm", "2": "in"}
DOC_TYPE = {
    "0": "passport",
    "1": "visa",
    "2": "driving_licence",
    "3": "id_card",
    "4": "other",
}

# Country-code corrections for known errors in the app export.
CODE_FIXES = {
    "belgium_driving_license": "BE",   # was exported as BY (Belarus)
    "brazil_driving_license": "BR",    # was exported as BE (Belgium)
}

COUNTRY_NAME_OVERRIDES = {
    "bosnia_and_herzegovina": "Bosnia and Herzegovina",
    "burkina_faso": "Burkina Faso",
    "congo_drc": "DR Congo",
    "congo_republic": "Republic of the Congo",
    "czech_republic": "Czech Republic",
    "european_union": "European Union",
    "guinea_bissau": "Guinea-Bissau",
    "hong_kong": "Hong Kong SAR (China)",
    "ivory_coast": "Cote d'Ivoire",
    "macau": "Macao SAR (China)",
    "north_macedonia": "North Macedonia",
    "palestinian_territories": "Palestinian Territories",
    "papua_new_guinea": "Papua New Guinea",
    "Saint Kitts and Nevis": "Saint Kitts and Nevis",
    "saint_kitts_and_nevis": "Saint Kitts and Nevis",
    "saudi_arabia": "Saudi Arabia",
    "south_africa": "South Africa",
    "south_korea": "South Korea",
    "sri_lanka": "Sri Lanka",
    "united_arab_emirates": "United Arab Emirates",
    "united_kingdom": "United Kingdom",
    "united_states": "United States",
    "new_zealand": "New Zealand",
    "Djibouti": "Djibouti",
}

# Country guide pages that exist on idphotowork.com (passport pages only).
GUIDE_PAGES = {
    "argentina", "australia", "bangladesh", "brazil", "china", "egypt", "france",
    "germany", "hong-kong", "india", "ireland", "italy", "japan", "kenya",
    "malaysia", "mexico", "netherlands", "new-zealand", "nigeria", "pakistan",
    "philippines", "poland", "russia", "saudi-arabia", "singapore", "south-africa",
    "south-korea", "spain", "switzerland", "thailand", "turkey", "uk", "us",
    "vietnam",
}
GUIDE_SLUG_OVERRIDES = {
    "united_states": "us",
    "united_kingdom": "uk",
    "hong_kong": "hong-kong",
    "new_zealand": "new-zealand",
    "saudi_arabia": "saudi-arabia",
    "south_africa": "south-africa",
    "south_korea": "south-korea",
}
SITE = "https://www.idphotowork.com"

# Verified corrections applied on top of the raw export.
# Every entry needs an official source, because the public dataset must be auditable.
CORRECTIONS = {
    # The Dutch national photo standard is an exception to the Schengen 32-36 mm
    # rule: chin-to-crown is 26-30 mm for anyone aged 11 or over, and it applies
    # to passports, identity cards and driving licences alike.
    "netherlands_passport": {
        "headMinMm": 26, "headMaxMm": 30,
        "source": "https://www.government.nl/topics/identification-documents/requirements-for-photos",
    },
    "dutch_id_card": {
        "headMinMm": 26, "headMaxMm": 30,
        "source": "https://www.government.nl/topics/identification-documents/requirements-for-photos",
    },
    "dutch_driving_license": {
        "headMinMm": 26, "headMaxMm": 30,
        "source": "https://www.government.nl/topics/identification-documents/requirements-for-photos",
    },
    # The export carried a light grey target for these four, while the issuing
    # authorities require plain white. Corrected against the published guides.
    "japan_passport": {"backgroundColor": "#ffffff", "source": f"{SITE}/japan-passport-photo.html"},
    "saudi_arabia_passport": {"backgroundColor": "#ffffff", "source": f"{SITE}/saudi-arabia-passport-photo.html"},
    "turkey_passport": {"backgroundColor": "#ffffff", "source": f"{SITE}/turkey-passport-photo.html"},
    "vietnam_passport": {"backgroundColor": "#ffffff", "source": f"{SITE}/vietnam-passport-photo.html"},
}

# Documents that are kept as-is but flagged for manual verification.
REVIEW_EXTRA = {
    "netherlands_visa": "Dutch missions quote 26-30 mm, the Schengen baseline is 32-36 mm.",
    "netherlands_ov_chipkaart_online": "Uses the Dutch national photo standard; not separately verified.",
    "netherlands_theory_exam": "Uses the Dutch national photo standard; not separately verified.",
    "indonesia_passport": "51x51 mm looks like a rounded 2x2 in; the Indonesian passport photo is commonly quoted as 35x45 mm or 40x60 mm.",
}


def num(value):
    """Convert a raw string to int/float, or return None when empty."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    return int(parsed) if parsed.is_integer() else round(parsed, 4)


def boolean(value):
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in ("true", "1", "yes"):
        return True
    if text in ("false", "0", "no"):
        return False
    return None


def country_name(slug: str) -> str:
    if slug in COUNTRY_NAME_OVERRIDES:
        return COUNTRY_NAME_OVERRIDES[slug]
    return " ".join(part.capitalize() for part in slug.replace("-", "_").split("_"))


def guide_url(country_slug: str, doc_type: str) -> str | None:
    if doc_type != "passport":
        return None
    page = GUIDE_SLUG_OVERRIDES.get(country_slug, country_slug.replace("_", "-"))
    if page in GUIDE_PAGES:
        return f"{SITE}/{page}-passport-photo.html"
    return None


def dims_mm(record: dict):
    """Return (width_mm, height_mm) for print units, else None."""
    unit = record["unit"]
    if unit == "mm":
        return (record["width"], record["height"])
    if unit == "in":
        return (round(record["width"] * 25.4, 2), round(record["height"] * 25.4, 2))
    return None


def completeness(record: dict) -> int:
    keys = ("headMinMm", "headMaxMm", "eyeLineMinMm", "eyeLineMaxMm",
            "glassesAllowed", "expressionStrict", "expression", "recencyMonths")
    return sum(1 for key in keys if record.get(key) is not None)


def normalize(raw: dict) -> dict:
    unit = UNIT.get(str(raw.get("unit", "")), None)
    doc_type = DOC_TYPE.get(str(raw.get("type", "")), "other")
    country_slug = raw.get("country", "").strip()
    code = CODE_FIXES.get(raw.get("titleResName", ""), raw.get("countryCode", "")).strip().upper()

    record = {
        "id": num(raw.get("id")),
        "countryCode": code,
        "country": country_slug,
        "countryName": country_name(country_slug),
        "documentType": doc_type,
        "documentId": raw.get("titleResName", "").strip(),
        "width": num(raw.get("width")),
        "height": num(raw.get("height")),
        "unit": unit,
        "dpi": num(raw.get("dpi")),
        "backgroundColor": (raw.get("bgcolor") or "").strip().lower() or None,
    }

    mm = dims_mm(record) if unit in ("mm", "in") else None
    if mm:
        record["widthMm"], record["heightMm"] = mm
    if unit == "px":
        record["pixelWidth"] = record["width"]
        record["pixelHeight"] = record["height"]

    for src, dst in (
        ("headMinMm", "headMinMm"),
        ("headMaxMm", "headMaxMm"),
        ("eyeLineMinMm", "eyeLineMinMm"),
        ("eyeLineMaxMm", "eyeLineMaxMm"),
        ("recencyMonths", "recencyMonths"),
    ):
        value = num(raw.get(src))
        if value is not None:
            record[dst] = value

    for src, dst in (("glassesAllowed", "glassesAllowed"), ("expressionStrict", "expressionStrict")):
        value = boolean(raw.get(src))
        if value is not None:
            record[dst] = value

    expression = (raw.get("expression") or "").strip()
    if expression:
        record["expression"] = expression

    guide = guide_url(country_slug, doc_type)
    if guide:
        record["guide"] = guide

    source = (raw.get("source") or "").strip()
    if source:
        record["source"] = source

    return record


def main() -> None:
    raw_rows = json.loads(RAW.read_text(encoding="utf-8"))
    if isinstance(raw_rows, dict):
        raw_rows = raw_rows.get("items", [])

    # Records verified after the app export was taken, kept in a separate file so
    # the export itself stays pristine.
    additions_path = ROOT / "data" / "source" / "additions.json"
    if additions_path.exists():
        raw_rows = raw_rows + json.loads(additions_path.read_text(encoding="utf-8"))

    records = [normalize(row) for row in raw_rows]
    records = [r for r in records if r["documentId"] and r["unit"]]

    unit_rank = {"mm": 3, "in": 2, "px": 1}
    groups: dict[tuple, list] = defaultdict(list)
    for record in records:
        groups[(record["countryCode"], record["documentId"])].append(record)

    merged, conflicts = [], []
    published = []
    for key, group in sorted(groups.items()):
        group.sort(key=lambda r: (-unit_rank.get(r["unit"], 0), -completeness(r), r["id"] or 0))
        primary = dict(group[0])

        # Apply verified corrections before anything is exported.
        fix = CORRECTIONS.get(primary["documentId"])
        if fix:
            for field, value in fix.items():
                if field == "source":
                    primary["source"] = value
                else:
                    primary[field] = value

        note = REVIEW_EXTRA.get(primary["documentId"])
        if note:
            primary["needsReview"] = True
            primary["reviewNote"] = note

        # Attach the pixel variant of the same document when both exist.
        px = next((r for r in group if r["unit"] == "px"), None)
        if px and primary["unit"] != "px":
            primary["pixelWidth"] = px["pixelWidth"]
            primary["pixelHeight"] = px["pixelHeight"]

        sizes = {dims_mm(r) for r in group if dims_mm(r)}
        dims_conflict = len({(w, h) for w, h in sizes}) > 1
        if dims_conflict:
            primary["needsReview"] = True
            conflicts.append({
                "countryCode": key[0],
                "documentId": key[1],
                "kept": {"width": primary["width"], "height": primary["height"], "unit": primary["unit"]},
                "alternatives": [
                    {"id": r["id"], "width": r["width"], "height": r["height"],
                     "unit": r["unit"], "backgroundColor": r.get("backgroundColor")}
                    for r in group[1:]
                ],
            })

        if len(group) > 1:
            merged.append({
                "countryCode": key[0],
                "documentId": key[1],
                "rows": len(group),
                "keptId": primary["id"],
                "droppedIds": [r["id"] for r in group[1:]],
                "conflict": dims_conflict,
            })

        published.append(primary)

    published.sort(key=lambda r: (r["countryName"], r["documentType"], r["documentId"]))

    # Re-number ids so the public dataset is stable and gap-free.
    for index, record in enumerate(published, start=1):
        record["id"] = index

    (ROOT / "data" / "specs.json").write_text(
        json.dumps(published, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    columns = [
        "id", "countryCode", "country", "countryName", "documentType", "documentId",
        "width", "height", "unit", "widthMm", "heightMm", "pixelWidth", "pixelHeight",
        "dpi", "backgroundColor", "headMinMm", "headMaxMm", "eyeLineMinMm",
        "eyeLineMaxMm", "glassesAllowed", "expressionStrict", "expression",
        "recencyMonths", "guide", "source", "needsReview", "reviewNote",
    ]
    with (ROOT / "data" / "specs.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for record in published:
            writer.writerow({key: record.get(key, "") for key in columns})

    country_counts = Counter(r["countryCode"] for r in published)
    countries = {}
    for record in published:
        countries.setdefault(record["countryCode"], {
            "countryCode": record["countryCode"],
            "country": record["country"],
            "countryName": record["countryName"],
        })
    country_index = [
        {**info, "documents": country_counts[code]}
        for code, info in sorted(countries.items(), key=lambda kv: kv[1]["countryName"])
    ]

    type_counts = Counter(r["documentType"] for r in published)
    with_compliance = sum(1 for r in published if r.get("headMinMm") is not None)
    index = {
        "name": "IDPhotoWork Document Photo Specs",
        "version": "1.0.0",
        "generated": date.today().isoformat(),
        "license": "CC BY 4.0",
        "homepage": SITE,
        "documents": len(published),
        "countries": len(country_counts),
        "documentsWithHeadHeight": with_compliance,
        "documentsNeedingReview": sum(1 for r in published if r.get("needsReview")),
        "byDocumentType": dict(sorted(type_counts.items())),
        "sourceRows": len(raw_rows),
        "countriesIndex": country_index,
    }
    (ROOT / "data" / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    by_country_dir = ROOT / "data" / "by-country"
    for stale in by_country_dir.glob("*.json"):
        stale.unlink()
    grouped = defaultdict(list)
    for record in published:
        grouped[record["countryCode"]].append(record)
    for code, rows in grouped.items():
        (by_country_dir / f"{code}.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    report = {
        "generated": date.today().isoformat(),
        "sourceRows": len(raw_rows),
        "publishedRecords": len(published),
        "mergedGroups": len(merged),
        "conflicts": len(conflicts),
        "notes": [
            "Groups below share the same (countryCode, documentId) but disagree on size.",
            "The kept row prefers millimetre sizes and rows with more compliance fields.",
            "Records flagged needsReview=true should be verified against an official source.",
        ],
        "merged": merged,
        "conflictsDetail": conflicts,
    }
    (ROOT / "data" / "quality-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"source rows        : {len(raw_rows)}")
    print(f"published records  : {len(published)}")
    print(f"countries          : {len(country_counts)}")
    print(f"merged duplicates  : {len(merged)} groups")
    print(f"needs review       : {len(conflicts)}")
    print(f"by document type   : {dict(sorted(type_counts.items()))}")


if __name__ == "__main__":
    main()
