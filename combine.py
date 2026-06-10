"""
Combine all scraped province/territory/federal CSVs into one unified file.
Output: data/all_entities.csv
"""
import csv
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# ── Unified schema ────────────────────────────────────────────────────────────
FIELDS = [
    "province", "type", "name", "about", "priorities",
    "website", "phone", "email", "address",
    "parent_ministry",
    "minister_name", "minister_phone", "minister_email",
    "minister_url", "minister_photo_url",
    "twitter", "facebook", "youtube", "instagram",
]

# ── Column aliases (source -> unified) ────────────────────────────────────────
# Applied after direct-match, first-write-wins per unified field.
ALIASES = {
    # Legacy AB / FED / NU ministry schema
    "photo_url":               "minister_photo_url",
    "minister_contact_number": "minister_phone",
    "emails":                  "email",
    # Legacy AB agency schema
    "agency_name":             "name",
    "agency_url":              "website",
    "classification":          "type",
    "description":             "about",   # agency description -> about
    # Legacy QC ministry schema (capital letters)
    "Type":                    "type",
    "Ministry":                "name",
    "About":                   "about",
    "Priorities":              "priorities",
    "Website":                 "website",
    "Minister(s)":             "minister_name",
    "Contact":                 "minister_url",
    "Biography":               "minister_url",
    # New agency schema uses "description" for the entity description
    # (same alias as AB, already mapped above)
}

# ── Files to skip ─────────────────────────────────────────────────────────────
SKIP_STEMS = {
    "agency_members_ab",   # board-member roster — different entity type
    "nunavut_agencies",    # empty
    "all_entities",        # the output file itself
}


def _province_from_path(p: Path) -> str:
    """data/AB/ministries.csv -> 'AB'"""
    parts = p.parts
    for i, part in enumerate(parts):
        if part == "data" and i + 1 < len(parts):
            candidate = parts[i + 1]
            if candidate.upper() == candidate and len(candidate) <= 3:
                return candidate
    return ""


def _default_type(stem: str) -> str:
    s = stem.lower()
    if any(x in s for x in ("ministr", "dept", "departm")):
        return "Ministry / Department"
    if "agenc" in s:
        return "Agency"
    return ""


def _is_legacy_ministry_schema(headers) -> bool:
    """AB/FED/NU ministry files: 'type' holds ministry name, 'name' holds minister name."""
    return "photo_url" in headers and "minister_contact_number" in headers


def _map_row(raw: dict, province: str, stem: str, legacy_ministry: bool = False) -> dict:
    out = {k: "" for k in FIELDS}

    # Province — prefer value already in the row
    out["province"] = (raw.get("province") or province or "").strip()

    for col, val in raw.items():
        if col == "province":
            continue
        val = (val or "").strip()
        if not val:
            continue

        # Legacy ministry schema: swap type ↔ name so they land in the right columns
        if legacy_ministry:
            if col == "type":
                col = "name"          # ministry name  -> name
            elif col == "name":
                col = "minister_name" # minister name  -> minister_name

        if col in FIELDS:
            if not out[col]:
                out[col] = val
        elif col in ALIASES:
            target = ALIASES[col]
            if not out[target]:
                out[target] = val

    if not out["type"]:
        out["type"] = _default_type(stem)

    return out


def _iter_csvs():
    """Yield (Path, province, encoding) for every CSV we want to include."""
    data_dir = ROOT / "data"
    if data_dir.exists():
        for p in sorted(data_dir.rglob("*.csv")):
            if p.stem in SKIP_STEMS:
                continue
            province = _province_from_path(p)
            yield p, province, "utf-8"

    # Root-level legacy files (e.g. quebec_ministries.csv)
    for p in sorted(ROOT.glob("*.csv")):
        if p.stem in SKIP_STEMS:
            continue
        # Skip files already captured in data/ to avoid duplicates
        if p.stem in {q.stem for q in (ROOT / "data").rglob("*.csv")}:
            continue
        province = "QC" if "quebec" in p.stem.lower() else ""
        yield p, province, "utf-8-sig"


def combine(output="data/all_entities.csv"):
    out_path = ROOT / output
    os.makedirs(out_path.parent, exist_ok=True)

    all_rows = []
    files_read = 0

    for csv_path, province, enc in _iter_csvs():
        # Skip the output file if it already exists
        if csv_path.resolve() == out_path.resolve():
            continue
        try:
            with open(csv_path, encoding=enc, newline="") as fh:
                reader = csv.DictReader(fh)
                headers = reader.fieldnames or []
                legacy = _is_legacy_ministry_schema(headers)
                batch = [_map_row(r, province, csv_path.stem, legacy) for r in reader]
            # Drop completely empty rows (no name and no website)
            batch = [r for r in batch if r["name"] or r["website"]]
            all_rows.extend(batch)
            files_read += 1
            rel = csv_path.relative_to(ROOT) if csv_path.is_relative_to(ROOT) else csv_path.name
            print(f"  {str(rel):<55}  {len(batch):>5} rows")
        except Exception as e:
            print(f"  [WARN] {csv_path.name}: {e}")

    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n  Combined {len(all_rows):,} rows from {files_read} files")
    print(f"  -> {out_path.relative_to(ROOT)}")
    return len(all_rows)


if __name__ == "__main__":
    print("Combining all CSV files…\n")
    combine()
