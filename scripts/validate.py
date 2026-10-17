#!/usr/bin/env python3
"""Validate the published dataset.

Usage:
    python3 scripts/validate.py

Checks structural rules, cross-file consistency and range sanity. Exits with a
non-zero status when any check fails, so it can run in CI.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

REQUIRED = (
    "id", "countryCode", "country", "countryName", "documentType", "documentId",
    "width", "height", "unit", "dpi", "backgroundColor",
)
UNITS = {"mm", "in", "px"}
DOC_TYPES = {"passport", "visa", "driving_licence", "id_card", "other"}
HEX = re.compile(r"^#[0-9a-f]{6}$")
CODE = re.compile(r"^[A-Z]{2}$")

errors: list[str] = []
warnings: list[str] = []


def fail(message: str) -> None:
    errors.append(message)


def main() -> int:
    specs = json.loads((DATA / "specs.json").read_text(encoding="utf-8"))
    index = json.loads((DATA / "index.json").read_text(encoding="utf-8"))

    if not isinstance(specs, list):
        fail("specs.json must be a JSON array")
        print("\n".join(errors))
        return 1

    seen = set()
    ids = []
    by_country: dict[str, list] = {}

    for position, record in enumerate(specs):
        where = f"record #{position} ({record.get('documentId', '?')})"

        for field in REQUIRED:
            if field not in record:
                fail(f"{where}: missing required field {field}")
        if any(field not in record for field in REQUIRED):
            continue

        ids.append(record["id"])
        if not isinstance(record["id"], int):
            fail(f"{where}: id must be an integer")
        if not CODE.match(record["countryCode"]):
            fail(f"{where}: countryCode {record['countryCode']!r} is not uppercase ISO alpha-2")
        if record["unit"] not in UNITS:
            fail(f"{where}: unknown unit {record['unit']!r}")
        if record["documentType"] not in DOC_TYPES:
            fail(f"{where}: unknown documentType {record['documentType']!r}")
        if not HEX.match(record["backgroundColor"]):
            fail(f"{where}: backgroundColor {record['backgroundColor']!r} is not lowercase hex")

        for dimension in ("width", "height"):
            if not isinstance(record[dimension], (int, float)) or record[dimension] <= 0:
                fail(f"{where}: {dimension} must be a positive number")

        if not isinstance(record["dpi"], int) or not 72 <= record["dpi"] <= 2400:
            fail(f"{where}: dpi out of range")

        key = (record["countryCode"], record["documentId"])
        if key in seen:
            fail(f"{where}: duplicate (countryCode, documentId) = {key}")
        seen.add(key)

        if record["unit"] in ("mm", "in"):
            if "widthMm" not in record or "heightMm" not in record:
                fail(f"{where}: print-size record is missing widthMm/heightMm")
            else:
                expected_w = record["width"] if record["unit"] == "mm" else record["width"] * 25.4
                expected_h = record["height"] if record["unit"] == "mm" else record["height"] * 25.4
                if abs(record["widthMm"] - expected_w) > 0.05:
                    fail(f"{where}: widthMm {record['widthMm']} does not match width {record['width']} {record['unit']}")
                if abs(record["heightMm"] - expected_h) > 0.05:
                    fail(f"{where}: heightMm {record['heightMm']} does not match height {record['height']} {record['unit']}")
                if not 10 <= record["widthMm"] <= 300 or not 10 <= record["heightMm"] <= 400:
                    fail(f"{where}: implausible print size {record['widthMm']}x{record['heightMm']} mm")
        if record["unit"] == "px":
            if "pixelWidth" not in record or "pixelHeight" not in record:
                fail(f"{where}: pixel record is missing pixelWidth/pixelHeight")
            elif record["pixelWidth"] < 100 or record["pixelHeight"] < 100:
                warnings.append(f"{where}: unusually small pixel size {record['pixelWidth']}x{record['pixelHeight']}")

        for low, high, label in (
            ("headMinMm", "headMaxMm", "head height"),
            ("eyeLineMinMm", "eyeLineMaxMm", "eye line"),
        ):
            if (low in record) != (high in record):
                fail(f"{where}: {label} has only one bound")
            elif low in record:
                if record[low] > record[high]:
                    fail(f"{where}: {label} min {record[low]} > max {record[high]}")
                if not 5 <= record[low] <= 200 or not 5 <= record[high] <= 200:
                    fail(f"{where}: {label} out of plausible range")

        if "recencyMonths" in record and not 1 <= record["recencyMonths"] <= 120:
            fail(f"{where}: recencyMonths out of range")

        if "guide" in record and not record["guide"].startswith("https://www.idphotowork.com/"):
            fail(f"{where}: guide must point at idphotowork.com")

        by_country.setdefault(record["countryCode"], []).append(record)

    if ids != list(range(1, len(specs) + 1)):
        fail("ids are not a gap-free sequence starting at 1")

    if index.get("documents") != len(specs):
        fail(f"index.documents {index.get('documents')} != {len(specs)} records")
    if index.get("countries") != len(by_country):
        fail(f"index.countries {index.get('countries')} != {len(by_country)} country files")

    count_by_type = Counter(record["documentType"] for record in specs)
    if index.get("byDocumentType") != dict(sorted(count_by_type.items())):
        fail("index.byDocumentType does not match specs.json")

    country_dir = DATA / "by-country"
    files = sorted(country_dir.glob("*.json"))
    if len(files) != len(by_country):
        fail(f"by-country has {len(files)} files for {len(by_country)} countries")

    for code, rows in by_country.items():
        path = country_dir / f"{code}.json"
        if not path.exists():
            fail(f"missing data/by-country/{code}.json")
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload != rows:
            fail(f"data/by-country/{code}.json does not match specs.json")

    with_head = sum(1 for record in specs if "headMinMm" in record)
    if index.get("documentsWithHeadHeight") != with_head:
        fail(f"index.documentsWithHeadHeight {index.get('documentsWithHeadHeight')} != {with_head}")

    print(f"records            : {len(specs)}")
    print(f"countries          : {len(by_country)}")
    print(f"with head height   : {with_head}")
    print(f"flagged review     : {sum(1 for r in specs if r.get('needsReview'))}")

    if warnings:
        print("\nwarnings:")
        for warning in warnings[:20]:
            print("  -", warning)

    if errors:
        print(f"\n{len(errors)} error(s):")
        for error in errors[:40]:
            print("  -", error)
        return 1

    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
