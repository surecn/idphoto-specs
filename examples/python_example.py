#!/usr/bin/env python3
"""Minimal consumer example for the document photo specs dataset.

Run from the repository root:
    python3 examples/python_example.py
"""

from __future__ import annotations

import json
from pathlib import Path

SPECS_PATH = Path(__file__).resolve().parent.parent / "data" / "specs.json"


def load_specs(path: Path = SPECS_PATH) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def find(specs: list[dict], country_code: str, document_type: str = "passport") -> dict | None:
    """Return the first matching record, or None."""
    for spec in specs:
        if spec["countryCode"] == country_code.upper() and spec["documentType"] == document_type:
            return spec
    return None


def target_pixels(spec: dict, dpi: int = 300) -> tuple[int, int]:
    """Print size converted to pixels at the given resolution."""
    if spec["unit"] == "px":
        return spec["pixelWidth"], spec["pixelHeight"]
    return (
        round(spec["widthMm"] / 25.4 * dpi),
        round(spec["heightMm"] / 25.4 * dpi),
    )


def head_height_px(spec: dict, dpi: int = 300) -> tuple[int, int] | None:
    """Allowed chin-to-crown range in pixels, or None when unverified."""
    if "headMinMm" not in spec:
        return None
    return (
        round(spec["headMinMm"] / 25.4 * dpi),
        round(spec["headMaxMm"] / 25.4 * dpi),
    )


def main() -> None:
    specs = load_specs()
    print(f"loaded {len(specs)} records\n")

    for code, doc_type in (("JP", "passport"), ("US", "passport"), ("NL", "passport"), ("AR", "passport")):
        spec = find(specs, code, doc_type)
        if spec is None:
            print(f"{code} {doc_type}: not found")
            continue

        px = target_pixels(spec, dpi=spec.get("dpi", 300))
        head = head_height_px(spec, dpi=spec.get("dpi", 300))
        unit_note = f"{spec['width']}x{spec['height']} {spec['unit']}"
        print(f"{spec['countryName']} ({code}) {doc_type}")
        print(f"  size at {spec.get('dpi', 300)} dpi : {unit_note} -> {px[0]}x{px[1]} px")
        print(f"  background            : {spec['backgroundColor']}")
        if head:
            print(f"  head height           : {spec['headMinMm']}-{spec['headMaxMm']} mm -> {head[0]}-{head[1]} px")
        else:
            print("  head height           : not verified, do not enforce")
        print()

    # Records where the neutral-expression rule is legally binding, not a preference.
    strict = [s for s in specs if s.get("expressionStrict") is True]
    print(f"documents with a strict expression rule: {len(strict)}")
    print(", ".join(sorted({s['countryName'] for s in strict})[:15]) + " ...")


if __name__ == "__main__":
    main()
