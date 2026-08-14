# @title 1 — DATA INGESTION & ENTITY RESOLUTION
# Inputs: Gettel .xlsx + any number of CORES companies/directors CSV batches
# Outputs: graph_data.json, dashboard_data.json, gettel_scrape_list.csv, gettel_transactions_parsed.csv

import pandas as pd
import json
import re
import io
import os
import sys
import glob
from datetime import datetime
from collections import defaultdict
import openpyxl

try:
    from google.colab import files
    IN_COLAB = True
except ImportError:
    IN_COLAB = False

# ── 1A: LOAD FILES ───────────────────────────────────────────────────────────
# Upload the Gettel .xlsx plus ALL of your CORES scrape batches at once — any
# number of "*companies*.csv" / "*directors*.csv" pairs (original scrape,
# "deep" phase, and any later re-scrape rounds). They're all merged and
# deduped together below, so you don't need to track which batch is which.
#
# Two ways to run this:
#   - In Colab: paste into a cell and run it — the file picker below opens.
#   - Locally: `python block1_data_prep.py <input_dir>` — every .xlsx/.csv in
#     <input_dir> (default: current directory) is picked up the same way,
#     matched by the same filename patterns, no upload dialog involved.

if IN_COLAB:
    print("=" * 60)
    print("UPLOAD REQUIRED — Gettel .xlsx + all CORES companies/directors CSVs")
    print("=" * 60)
    print()
    print("Select the Gettel .xlsx AND every cores_companies*.csv /")
    print("cores_directors*.csv batch you have (Ctrl+click / Cmd+click).")
    print("=" * 60)

    uploaded = files.upload()
    if not uploaded:
        raise RuntimeError("No files uploaded. Re-run this cell and upload your files.")
    uploaded_names = list(uploaded.keys())
    read_bytes = lambda name: uploaded[name]
else:
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    found = sorted(glob.glob(os.path.join(input_dir, "*.xlsx")) + glob.glob(os.path.join(input_dir, "*.csv")))
    if not found:
        raise RuntimeError(f"No .xlsx/.csv files found in '{input_dir}'. "
                            f"Pass the folder containing the Gettel .xlsx and CORES CSVs as an argument.")
    uploaded_names = [os.path.basename(p) for p in found]
    _paths = {os.path.basename(p): p for p in found}
    read_bytes = lambda name: open(_paths[name], "rb").read()
    print(f"Reading from local directory: {os.path.abspath(input_dir)}")

print(f"\nFound {len(uploaded_names)} file(s):")
for n in uploaded_names:
    print(f"  {n}")

# ── Match uploaded files by pattern ──────────────────────────────────────────

gettel_file    = next((n for n in uploaded_names if n.lower().endswith('.xlsx')), None)
company_files  = [n for n in uploaded_names if 'companies' in n.lower()]
director_files = [n for n in uploaded_names if 'directors' in n.lower()]

missing = []
if not gettel_file:     missing.append("Gettel .xlsx")
if not company_files:   missing.append("cores_companies*.csv (at least one batch)")
if not director_files:  missing.append("cores_directors*.csv (at least one batch)")

if missing:
    where = "Re-run the cell and upload" if IN_COLAB else "Add to the input directory"
    raise FileNotFoundError(
        f"\nMissing files — could not identify:\n" +
        "\n".join(f"  - {m}" for m in missing) +
        f"\n\nFound: {uploaded_names}\n"
        f"{where} the Gettel .xlsx plus your CORES CSV batches."
    )

print(f"\nFile mapping:")
print(f"  Gettel              → {gettel_file}")
print(f"  Company CSV batches → {len(company_files)}: {company_files}")
print(f"  Director CSV batches→ {len(director_files)}: {director_files}")

# Known Gettel-name typos that will never string-match their real CORES name
# (usually OCR misreads from the source PDFs). Add entries here as you find
# them: normalized Gettel entity name -> normalized CORES Legal_Name.
GETTEL_NAME_ALIASES = {
    "BLT PROPERTY RENTAL INC": "LTD PROPERTY RENTALS INC",
}

# ── 1A: LOAD SOURCES ─────────────────────────────────────────────────────────

print("\nLoading Gettel...")
wb = openpyxl.load_workbook(io.BytesIO(read_bytes(gettel_file)), data_only=True)
ws = wb[wb.sheetnames[0]]
rows = list(ws.iter_rows(values_only=True))
gettel_headers = rows[0]
_hidx = {h: i for i, h in enumerate(gettel_headers)}

# Column names vary between Gettel export versions (e.g. "Sale Year" vs
# "Year Sold", or a raw single "Vendor"/"Purchaser" field vs. pre-split
# "Vendor Company"/"Vendor Director" columns). Look up by name with
# fallbacks instead of hardcoded positions so both layouts work, and so a
# reordered/renamed column doesn't silently read the wrong field.
GETTEL_COLMAP = {
    'prop_id':            ['Prop ID'],
    'property_class':     ['Property Class'],
    'property_type':      ['Property Type'],
    'ownership_type':     ['Ownership Type'],
    'description':        ['Description'],
    'land_use':           ['Land Use Class'],
    'address':            ['Address'],
    'city':                ['City'],
    'vendor_raw':         ['Vendor'],
    'purchaser_raw':      ['Purchaser'],
    'vendor_company':     ['Vendor Company'],
    'vendor_director':    ['Vendor Director'],
    'purchaser_company':  ['Purchaser Company'],
    'purchaser_director': ['Purchaser Director'],
    'legal_description':  ['Legal Description'],
    'subdivision':        ['Subdivision'],
    'site_area':          ['Site Area'],
    'site_units':         ['Site Units'],
    'bldg_area':          ['Bldg Area'],
    'bldg_units':         ['Bldg Units'],
    'sale_price':         ['Sale Price'],
    'sale_date':          ['Sale Date'],
    'sale_year':          ['Year Sold', 'Sale Year'],
    'unit_price':         ['Unit Price'],
    'unit_measure':       ['Unit Price Measure'],
    'year_built':         ['Year Built'],
    'cap_rate':           ['Cap Rate'],
    'total_units':        ['Total Units'],
}

def gv(row, field):
    # pd.notna() catches both None and NaN float cells (a blank Excel cell
    # loads as float('nan'), which is truthy in Python — "x or ''" silently
    # keeps the NaN instead of falling through, and str(nan) becomes the
    # literal string "nan" downstream). Checking notna() here means every
    # blank cell resolves to None at this single choke point, so every
    # "gv(r, field) or default" call site below is safe without repeating
    # the NaN check at each one.
    for name in GETTEL_COLMAP.get(field, []):
        i = _hidx.get(name)
        if i is not None and pd.notna(row[i]):
            return row[i]
    return None

# Drop fully-blank padding rows some exports leave at the bottom of the sheet
data_rows = [r for r in rows[1:] if gv(r, "property_class") is not None]
gettel_raw = pd.DataFrame(data_rows, columns=gettel_headers)
print(f"  Gettel: {len(gettel_raw)} real rows (of {len(rows)-1} total, blanks dropped), {len(gettel_raw.columns)} cols")

print("Loading CORES...")

def _load_cores_batch(name):
    df = pd.read_csv(io.BytesIO(read_bytes(name)), dtype=str)
    if "depth" not in df.columns:
        df["depth"] = "1"
        df["parent_CAN"] = ""
    return df

all_companies = pd.concat([_load_cores_batch(n) for n in company_files], ignore_index=True)
all_directors = pd.concat([_load_cores_batch(n) for n in director_files], ignore_index=True)
print(f"  CORES (raw, {len(company_files)} company batch(es) + {len(director_files)} director batch(es)): "
      f"{len(all_companies)} companies, {len(all_directors)} director records")

# ── 1A: DEDUPE ───────────────────────────────────────────────────────────────
# The scraper re-visits companies across runs/phases and re-appends rows, so the
# same CAN (and the same director) can show up several times. Most repeats are
# byte-for-byte identical, but a few are the same company/director scraped at
# different points in time (a new annual return filed, a status change, a
# parent_CAN only found once the deep crawl ran). We keep one row per key,
# preferring the most complete / most recently-filed version rather than just
# the first one seen, so we don't silently regress a status or drop a
# parent_CAN link that a later scrape picked up.

def _completeness(df, ignore_cols=()):
    """Count of non-null, non-empty-string fields per row (higher = richer record)."""
    scored = df.drop(columns=[c for c in ignore_cols if c in df.columns])
    return scored.apply(lambda col: col.notna() & (col.astype(str).str.strip() != ""), axis=0).sum(axis=1)

def dedupe_companies(df):
    df = df.copy()
    ar_year = pd.to_numeric(df.get("Last_AR_Year"), errors="coerce").fillna(-1)
    completeness = _completeness(df, ignore_cols=["CAN"])
    df = (df.assign(_ar_year=ar_year, _completeness=completeness)
            .sort_values(["_ar_year", "_completeness"], ascending=[False, False])
            .drop(columns=["_ar_year", "_completeness"]))
    before = len(df)
    df = df.drop_duplicates(subset=["CAN"], keep="first").reset_index(drop=True)
    print(f"  Deduped companies: {before} -> {len(df)} ({before - len(df)} duplicate rows removed)")
    return df

def dedupe_directors(df):
    # Appointment_Date is part of the key: a person can resign and be
    # reappointed later, which is two legitimate records, not a duplicate.
    key_cols = ["CAN", "Last_Name", "First_Name", "Type", "Appointment_Date"]
    df = df.copy()
    completeness = _completeness(df, ignore_cols=key_cols)
    df = (df.assign(_completeness=completeness)
            .sort_values("_completeness", ascending=False)
            .drop(columns=["_completeness"]))
    before = len(df)
    df = df.drop_duplicates(subset=key_cols, keep="first").reset_index(drop=True)
    print(f"  Deduped directors: {before} -> {len(df)} ({before - len(df)} duplicate rows removed)")
    return df

all_companies = dedupe_companies(all_companies)
all_directors = dedupe_directors(all_directors)
print(f"  CORES (deduped): {len(all_companies)} companies, {len(all_directors)} director records")

# ── 1A: NORMALIZE ────────────────────────────────────────────────────────────

CORP_KEYWORDS = [
    r'\bLTD\.?\b', r'\bINC\.?\b', r'\bCORP\.?\b', r'\bCORPORATION\b',
    r'\bLIMITED\b', r'\bHOLDINGS\b', r'\bENTERPRISES\b', r'\bPROPERTIES\b',
    r'\bREALTY\b', r'\bDEVELOPMENTS?\b', r'\bINVESTMENTS?\b', r'\bGROUP\b',
    r'\bPARTNERS?\b', r'\bASSOCIATES?\b', r'\bCAPITAL\b', r'\bMANAGEMENT\b',
    r'\bRESIDENCES?\b', r'\bVENTURES?\b', r'\bINDUSTRIES\b', r'\bSERVICES\b',
    r'\bL\.L\.C\b', r'\bLLP\b', r'\bLP\b', r'\bTRUST\b',
]
CORP_RE = re.compile('|'.join(CORP_KEYWORDS), re.I)

GOVT_KEYWORDS = [
    'CITY OF', 'TOWN OF', 'COUNTY OF', 'MUNICIPALITY OF', 'PROVINCE OF',
    'ALBERTA INFRASTRUCTURE', 'ALBERTA TRANSPORTATION', 'GOVERNMENT OF',
    'FEDERAL', 'CROWN', 'SCHOOL BOARD', 'SCHOOL DIVISION',
]

ET_AL_RE    = re.compile(r'\s*(Et,?\s*al\.?|et\s*al\.?)\s*$', re.I)
ROLE_RE     = re.compile(r'^(directors?|shareholders?|director/shareholder|dshareholder)[;:]?\s*(.*?)$', re.I)
NUMBERED_RE = re.compile(r'^\d{6,}')

def normalize(name):
    if not isinstance(name, str):
        return ""
    n = name.upper().strip()
    n = ET_AL_RE.sub('', n)
    n = re.sub(r'\s+', ' ', n)
    n = n.rstrip('.,;').strip()
    return n

def detect_entity_type(name):
    up = name.upper()
    for kw in GOVT_KEYWORDS:
        if kw in up:
            return "government"
    if NUMBERED_RE.match(name.strip()):
        return "company"
    if CORP_RE.search(name):
        return "company"
    return "individual"

def detect_province(name):
    up = name.upper()
    if re.search(r'\bALBERTA\b|^\d+\s+ALBERTA', up):
        return "AB"
    if re.search(r'\bB\.C\.\b|\bBC\b|\bBRITISH COLUMBIA\b', up):
        return "BC"
    if re.search(r'\bONTARIO\b|\bONT\.\b', up):
        return "ON"
    if re.search(r'\bSASKATCHEWAN\b|\bMANITOBA\b|\bQUEBEC\b|\bNOVA SCOTIA\b', up):
        return "OTHER"
    return "unknown"

cores_can_lookup = {normalize(row["Legal_Name"]): str(row["CAN"]) for _, row in all_companies.iterrows()}

# ── 1B: PARSE GETTEL VENDOR / PURCHASER ──────────────────────────────────────

def parse_party(raw_text):
    if not isinstance(raw_text, str) or not raw_text.strip():
        return {"entity":"", "entity_type":"", "person":"", "role":"", "address":"", "is_et_al":False}

    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    if not lines:
        return {"entity":"", "entity_type":"", "person":"", "role":"", "address":"", "is_et_al":False}

    raw_entity = lines[0]
    is_et_al   = bool(ET_AL_RE.search(raw_entity))
    entity     = ET_AL_RE.sub('', raw_entity).strip()
    entity_type= detect_entity_type(entity)

    person  = ""
    role    = ""
    addr_lines = []

    if len(lines) > 1:
        idx = 1
        m = ROLE_RE.match(lines[idx]) if idx < len(lines) else None
        if m:
            raw_role = m.group(1).lower()
            role = "Shareholder" if "share" in raw_role else "Director"
            inline_name = m.group(2).strip()
            if inline_name:
                person = inline_name
                idx += 1
            else:
                idx += 1
                if idx < len(lines) and not is_address_line(lines[idx]):
                    person = lines[idx]
                    idx += 1
            addr_lines = lines[idx:]
        else:
            if entity_type == "individual":
                addr_lines = lines[1:]
            else:
                if idx < len(lines) and not is_address_line(lines[idx]):
                    person = lines[idx]
                    idx += 1
                addr_lines = lines[idx:]

    address = ", ".join(addr_lines)
    return {"entity": entity, "entity_type": entity_type, "person": person,
            "role": role, "address": address, "is_et_al": is_et_al}

def is_address_line(line):
    if re.match(r'^\d{1,6}\s', line):
        return True
    if re.match(r'^(Box|Suite|Unit|RR|PO|P\.O\.)', line, re.I):
        return True
    if re.search(r'\b(AB|BC|ON|SK|MB|QC)\b\s+[A-Z]\d[A-Z]', line):
        return True
    return False

def apply_presplit_override(parsed, company_val, person_val):
    # Some Gettel export versions flatten the vendor/purchaser text onto a
    # single line (no embedded newlines), which breaks parse_party's
    # line-splitting above and pollutes "entity" with the director's name
    # and address glued on. Those exports also carry pre-split Vendor/
    # Purchaser Company + Director columns built separately from the raw
    # text — prefer those for entity/person whenever present, and keep
    # parse_party's role/address (which degrade to "" rather than garbage
    # on the flattened rows, since len(lines) == 1 short-circuits them).
    company = str(company_val or '').strip()
    person  = str(person_val or '').strip()
    if company:
        parsed = dict(parsed)
        parsed["entity"] = company
        parsed["entity_type"] = detect_entity_type(company)
        parsed["is_et_al"] = bool(ET_AL_RE.search(company))
    if person:
        parsed = dict(parsed)
        parsed["person"] = person
    return parsed

print("Parsing Gettel vendor/purchaser fields...")
records = []
for i, row in gettel_raw.iterrows():
    r = row.values
    vp = apply_presplit_override(parse_party(gv(r, "vendor_raw")), gv(r, "vendor_company"), gv(r, "vendor_director"))
    pp = apply_presplit_override(parse_party(gv(r, "purchaser_raw")), gv(r, "purchaser_company"), gv(r, "purchaser_director"))

    def as_float(v):
        try: return float(v) if v not in (None, "") else None
        except: return None
    def as_int(v):
        try: return int(v) if v not in (None, "") else None
        except: return None

    sale_price = as_float(gv(r, "sale_price"))
    sale_date  = gv(r, "sale_date")
    sale_date_str = sale_date.strftime('%Y-%m-%d') if hasattr(sale_date, 'strftime') else str(sale_date or '')
    sale_year  = as_int(gv(r, "sale_year"))
    unit_price = as_float(gv(r, "unit_price"))
    unit_measure = str(gv(r, "unit_measure") or '').strip()
    site_area  = as_float(gv(r, "site_area"))
    bldg_area  = as_float(gv(r, "bldg_area"))
    year_built = as_int(gv(r, "year_built"))
    ownership_type = str(gv(r, "ownership_type") or '').strip().title()
    property_type_val = str(gv(r, "property_type") or '')

    # Cap Rate: Gettel fills unreported cap rates with 0 rather than leaving
    # the cell blank, so 0 has to be treated as "not reported," not a real
    # 0% cap rate — otherwise it drags down every average and shows up as a
    # bogus outlier in the filter range.
    cap_rate = as_float(gv(r, "cap_rate"))
    if cap_rate == 0:
        cap_rate = None
    total_units = as_int(gv(r, "total_units"))

    # Unit Price is measure-dependent (Suite/Unit vs Acre vs Sq Ft) — the
    # same column mixes $/door building deals with $/acre and $/sqft land
    # deals, so a single "price per unit" filter would compare unrelated
    # things. Split into two consistent buckets instead:
    #   price_per_door: Suite/Unit-measured deals only (Unit Price IS $/door
    #     already for these rows).
    #   price_per_acre: Acre-measured deals as-is; Sq Ft-measured LAND deals
    #     converted to an acre-equivalent (43,560 sqft/acre) so a parcel
    #     priced per sqft doesn't fall through the land filter. Sq Ft deals
    #     on actual buildings (a handful of rows) are left out of both
    #     buckets — too small a group, and not a land/door comparison either.
    SQFT_PER_ACRE = 43560
    price_per_door = None
    price_per_acre = None
    um = unit_measure.lower()
    if um in ('suite', 'unit') and unit_price is not None:
        price_per_door = unit_price
    elif um == 'acre' and unit_price is not None:
        price_per_acre = unit_price
    elif um == 'sq ft' and unit_price is not None and property_type_val.strip().lower() == 'land':
        price_per_acre = unit_price * SQFT_PER_ACRE

    records.append({
        "txn_id":             i,
        "prop_id":            str(gv(r, "prop_id") or ''),
        "property_class":     str(gv(r, "property_class") or ''),
        "property_type":      property_type_val,
        "ownership_type":     ownership_type,
        "description":        str(gv(r, "description") or ''),
        "land_use":           str(gv(r, "land_use") or ''),
        "address":            str(gv(r, "address") or ''),
        "city":               str(gv(r, "city") or ''),
        "legal_description":  str(gv(r, "legal_description") or ''),
        "subdivision":        str(gv(r, "subdivision") or ''),
        "site_area":          site_area,
        "site_units":         str(gv(r, "site_units") or ''),
        "bldg_area":          bldg_area,
        "bldg_units":         str(gv(r, "bldg_units") or ''),
        "sale_price":         sale_price,
        "sale_date":          sale_date_str,
        "sale_year":          sale_year,
        "unit_price":         unit_price,
        "unit_measure":       unit_measure,
        "price_per_door":     price_per_door,
        "price_per_acre":     price_per_acre,
        "cap_rate":           cap_rate,
        "total_units":        total_units,
        "year_built":         year_built,
        "vendor_raw":         str(gv(r, "vendor_raw") or ''),
        "vendor_entity":      vp["entity"],
        "vendor_entity_type": vp["entity_type"],
        "vendor_person":      vp["person"],
        "vendor_role":        vp["role"],
        "vendor_address":     vp["address"],
        "vendor_is_et_al":    vp["is_et_al"],
        "purchaser_raw":      str(gv(r, "purchaser_raw") or ''),
        "purchaser_entity":   pp["entity"],
        "purchaser_entity_type": pp["entity_type"],
        "purchaser_person":   pp["person"],
        "purchaser_role":     pp["role"],
        "purchaser_address":  pp["address"],
        "purchaser_is_et_al": pp["is_et_al"],
    })

gettel_txns = pd.DataFrame(records)

# Parse stats
print(f"\nParse summary:")
print(f"  Vendor entity types: {gettel_txns['vendor_entity_type'].value_counts().to_dict()}")
print(f"  Purchaser entity types: {gettel_txns['purchaser_entity_type'].value_counts().to_dict()}")
print(f"  Vendor roles: {gettel_txns['vendor_role'].value_counts().to_dict()}")
print(f"  Vendor et al: {gettel_txns['vendor_is_et_al'].sum()}")
print(f"  Purchaser et al: {gettel_txns['purchaser_is_et_al'].sum()}")

# ── 1C: ENTITY MATCHING ───────────────────────────────────────────────────────

print("\nMatching Gettel entities to CORES...")

def match_company(name):
    norm = normalize(name)
    if norm in cores_can_lookup:
        return cores_can_lookup[norm], "exact"
    # Try stripping common suffix variants
    alt = re.sub(r'\bLTD$|LIMITED$', 'LTD.', norm)
    if alt in cores_can_lookup:
        return cores_can_lookup[alt], "normalized"
    alt2 = norm.rstrip('.')
    if alt2 in cores_can_lookup:
        return cores_can_lookup[alt2], "normalized"
    if norm in GETTEL_NAME_ALIASES:
        aliased = GETTEL_NAME_ALIASES[norm]
        if aliased in cores_can_lookup:
            return cores_can_lookup[aliased], "aliased"
    return "", "unmatched"

vendor_cans    = {}
purchaser_cans = {}

for ent in gettel_txns["vendor_entity"].unique():
    if ent and detect_entity_type(ent) == "company":
        can, conf = match_company(ent)
        vendor_cans[ent] = can

for ent in gettel_txns["purchaser_entity"].unique():
    if ent and detect_entity_type(ent) == "company":
        can, conf = match_company(ent)
        purchaser_cans[ent] = can

gettel_txns["vendor_can"]    = gettel_txns["vendor_entity"].map(lambda e: vendor_cans.get(e, ""))
gettel_txns["purchaser_can"] = gettel_txns["purchaser_entity"].map(lambda e: purchaser_cans.get(e, ""))

matched_v = (gettel_txns["vendor_can"] != "").sum()
matched_p = (gettel_txns["purchaser_can"] != "").sum()
print(f"  Vendor matches: {matched_v} / {len(gettel_txns)}")
print(f"  Purchaser matches: {matched_p} / {len(gettel_txns)}")

# Related-party flag: same person named on both sides of the deal, or the
# vendor/purchaser companies share a CORES-matched individual director or
# shareholder. Flags likely non-arm's-length transfers (corporate
# restructurings, related-party sales) that would otherwise silently
# inflate "arm's length" volume/leaderboard stats.
person_keys_by_can = defaultdict(set)
for _, row in all_directors.iterrows():
    if str(row.get("Individual_or_Corp","")).strip() == "Individual":
        can = str(row.get("CAN","")).strip()
        last  = str(row.get("Last_Name","")).strip().upper()
        first = str(row.get("First_Name","")).strip().upper()
        if can and last:
            person_keys_by_can[can].add((last, first))

def _is_related_party(row):
    vp = str(row.get("vendor_person","")).strip().upper()
    pp = str(row.get("purchaser_person","")).strip().upper()
    if vp and pp and vp == pp:
        return True
    vcan = row.get("vendor_can","")
    pcan = row.get("purchaser_can","")
    if vcan and pcan and person_keys_by_can.get(vcan) and person_keys_by_can.get(pcan):
        if person_keys_by_can[vcan] & person_keys_by_can[pcan]:
            return True
    return False

gettel_txns["related_party"] = gettel_txns.apply(_is_related_party, axis=1)
print(f"  Related-party transactions flagged: {int(gettel_txns['related_party'].sum())} / {len(gettel_txns)}")

# Person matching
cores_person_lookup = defaultdict(list)
for _, row in all_directors.iterrows():
    if str(row.get("Individual_or_Corp","")).strip() == "Individual":
        last  = str(row.get("Last_Name","")).strip().upper()
        first = str(row.get("First_Name","")).strip().upper()
        if last:
            cores_person_lookup[(last, first)].append({
                "can":          str(row.get("CAN","")),
                "company_name": str(row.get("Company_Name","")),
                "role":         str(row.get("Type","")),
                "city":         str(row.get("City","")),
                "province":     str(row.get("Province","")),
            })

def split_person_name(full):
    parts = full.strip().split()
    if len(parts) >= 2:
        return parts[-1].upper(), " ".join(parts[:-1]).upper()
    return full.upper(), ""

person_edges = []
for _, row in gettel_txns.iterrows():
    for side in [("vendor","vendor_person","vendor_can"), ("purchaser","purchaser_person","purchaser_can")]:
        side_name, person_col, can_col = side
        person = str(row.get(person_col,"")).strip()
        company_can = str(row.get(can_col,"")).strip()
        if not person:
            continue
        last, first = split_person_name(person)
        matches = cores_person_lookup.get((last, first), [])
        if not matches:
            matches = cores_person_lookup.get((last, ""), [])
        for m in matches:
            confidence = "high_direct" if m["can"] == company_can and company_can else "low_name"
            person_edges.append({
                "person_name":   person,
                "person_key":    f"{last},{first}",
                "company_can":   company_can or m["can"],
                "txn_id":        int(row["txn_id"]),
                "confidence":    confidence,
                "role":          side_name,
            })

# Medium confidence: CORES directors of transacting companies not named in Gettel
transacting_cans = set(gettel_txns["vendor_can"].dropna()) | set(gettel_txns["purchaser_can"].dropna())
transacting_cans.discard("")
for _, row in all_directors.iterrows():
    if str(row.get("Individual_or_Corp","")).strip() != "Individual":
        continue
    can = str(row.get("CAN","")).strip()
    if can not in transacting_cans:
        continue
    last  = str(row.get("Last_Name","")).strip().upper()
    first = str(row.get("First_Name","")).strip().upper()
    person_key = f"{last},{first}"
    if not any(e["person_key"] == person_key and e["company_can"] == can for e in person_edges):
        person_edges.append({
            "person_name": f"{first} {last}".strip(),
            "person_key":  person_key,
            "company_can": can,
            "txn_id":      None,
            "confidence":  "medium_cores",
            "role":        str(row.get("Type","")).lower(),
        })

print(f"  Person edges built: {len(person_edges)}")

# ── 1D: BUILD GRAPH DATA ──────────────────────────────────────────────────────

print("\nBuilding graph_data.json...")

def safe_str(v):
    return "" if pd.isna(v) or v is None else str(v)

# Index transactions by CAN
txns_by_can = defaultdict(list)
for _, row in gettel_txns.iterrows():
    entry = {
        "txn_id":         int(row["txn_id"]),
        "sale_price":     row["sale_price"],
        "sale_date":      row["sale_date"],
        "property_class": row["property_class"],
        "property_type":  row["property_type"],
        "description":    row["description"],
        "address":        row["address"],
        "city":           row["city"],
        "site_area":      row["site_area"],
        "site_units":     row["site_units"],
        "bldg_area":      row["bldg_area"],
        "unit_price":     row["unit_price"],
        "year_built":     row["year_built"],
    }
    if row["vendor_can"]:
        txns_by_can[row["vendor_can"]].append({**entry, "role":"vendor",
            "counterparty": row["purchaser_entity"],
            "counterparty_person": row["purchaser_person"]})
    if row["purchaser_can"]:
        txns_by_can[row["purchaser_can"]].append({**entry, "role":"purchaser",
            "counterparty": row["vendor_entity"],
            "counterparty_person": row["vendor_person"]})

# Build directors index per company
dirs_by_can = defaultdict(list)
for _, row in all_directors.iterrows():
    can = safe_str(row.get("CAN",""))
    dirs_by_can[can].append({
        "id":           f"{safe_str(row.get('Last_Name',''))}_{safe_str(row.get('First_Name',''))}_{can}",
        "label":        f"{safe_str(row.get('Last_Name',''))}, {safe_str(row.get('First_Name',''))}".strip(', '),
        "node_type":    safe_str(row.get("Individual_or_Corp","individual")).lower(),
        "role":         safe_str(row.get("Type","")),
        "pct_shares":   safe_str(row.get("Percent_Voting_Shares","")),
        "status":       safe_str(row.get("Status","")),
        "appointment":  safe_str(row.get("Appointment_Date","")),
        "cessation":    safe_str(row.get("Cessation_Date","")),
        "address":      ", ".join(filter(None, [
                            safe_str(row.get("Street","")),
                            safe_str(row.get("City","")),
                            safe_str(row.get("Province","")),
                            safe_str(row.get("Postal",""))])),
        "corp_can":     safe_str(row.get("Director_Corp_CAN","")),
        "source":       "cores",
    })

company_info = {}

# CORES companies
for _, row in all_companies.iterrows():
    can = safe_str(row.get("CAN",""))
    txns = txns_by_can.get(can, [])
    company_info[can] = {
        "can":               can,
        "label":             safe_str(row.get("Legal_Name","")),
        "status":            safe_str(row.get("Status","")),
        "depth":             safe_str(row.get("depth","1")),
        "parent_can":        safe_str(row.get("parent_CAN","")),
        "city":              safe_str(row.get("Reg_City","")),
        "le_type":           safe_str(row.get("LE_Type","")),
        "corp_type":         safe_str(row.get("Corp_Type","")),
        "registration_date": safe_str(row.get("Registration_Date","")),
        "address":           ", ".join(filter(None, [
                                safe_str(row.get("Reg_Street","")),
                                safe_str(row.get("Reg_City","")),
                                safe_str(row.get("Reg_Province","")),
                                safe_str(row.get("Reg_Postal",""))])),
        "email":             safe_str(row.get("Email","")),
        "agent":             safe_str(row.get("Agent_For_Service","")),
        "last_ar_year":      safe_str(row.get("Last_AR_Year","")),
        "last_ar_filed":     safe_str(row.get("Last_AR_Filed","")),
        "all_annual_returns":safe_str(row.get("All_Annual_Returns","")),
        "source":            "cores" if not txns else "cores+gettel",
        "children":          dirs_by_can.get(can, []),
        "transactions":      txns,
    }

# Gettel-only companies (not in CORES)
all_cores_cans = set(company_info.keys())
gettel_only_entities = {}
for _, row in gettel_txns.iterrows():
    for side, can_col in [("vendor","vendor_can"),("purchaser","purchaser_can")]:
        ent  = row[f"{side}_entity"]
        can  = row[f"{side}_can"]
        etype= row[f"{side}_entity_type"]
        if ent and etype == "company" and (not can or can not in all_cores_cans):
            key = normalize(ent)
            if key not in gettel_only_entities:
                gettel_only_entities[key] = {"label": ent, "txns": [], "persons": {}}
            t_entry = {
                "txn_id":         int(row["txn_id"]),
                "sale_price":     row["sale_price"],
                "sale_date":      row["sale_date"],
                "property_class": row["property_class"],
                "description":    row["description"],
                "address":        row["address"],
                "city":           row["city"],
            }
            t_entry["role"] = side
            t_entry["counterparty"] = row["purchaser_entity" if side=="vendor" else "vendor_entity"]
            gettel_only_entities[key]["txns"].append(t_entry)
            person = row[f"{side}_person"]
            role   = row[f"{side}_role"]
            if person:
                gettel_only_entities[key]["persons"][person] = role

for key, data in gettel_only_entities.items():
    fake_can = f"GETTEL_{key[:30]}"
    children = [{"id": f"p_{normalize(p)}", "label": p, "node_type": "individual",
                 "role": r, "pct_shares":"","status":"","appointment":"",
                 "cessation":"","address":"","corp_can":"","source":"gettel"}
                for p, r in data["persons"].items()]
    company_info[fake_can] = {
        "can": fake_can, "label": data["label"], "status": "", "depth": "1",
        "parent_can": "", "city": "", "le_type": "", "corp_type": "",
        "registration_date": "", "address": "", "email": "", "agent": "",
        "last_ar_year": "", "last_ar_filed": "", "all_annual_returns": "",
        "source": "gettel_only", "children": children, "transactions": data["txns"],
    }

# Person index
person_index = defaultdict(lambda: {"label":"","companies":[],"transactions":[]})
for e in person_edges:
    key = e["person_key"]
    person_index[key]["label"] = e["person_name"]
    if e["company_can"] and e["company_can"] not in person_index[key]["companies"]:
        person_index[key]["companies"].append(e["company_can"])
    if e["txn_id"] is not None:
        person_index[key]["transactions"].append({
            "txn_id":     e["txn_id"],
            "confidence": e["confidence"],
            "company_can":e["company_can"],
            "role":       e["role"],
        })

company_list = [
    {"can": v["can"], "label": v["label"], "status": v["status"],
     "depth": v["depth"], "city": v["city"],
     "child_count": len(v["children"]), "txn_count": len(v["transactions"]),
     "source": v["source"]}
    for v in company_info.values()
]

graph_data = {
    "company_info": company_info,
    "company_list": company_list,
    "person_index": dict(person_index),
    "meta": {
        "total_companies": len(company_info),
        "total_persons":   len(person_index),
        "total_transactions": len(gettel_txns),
        "generated": datetime.now().strftime("%Y-%m-%d"),
    }
}

with open("graph_data.json","w",encoding="utf-8") as f:
    json.dump(graph_data, f, default=str)
print(f"  graph_data.json: {len(company_info)} companies, {len(person_index)} persons")

# ── 1E: BUILD DASHBOARD DATA ──────────────────────────────────────────────────

print("Building dashboard_data.json...")

txn_records = []
for _, row in gettel_txns.iterrows():
    txn_records.append({
        "txn_id":           int(row["txn_id"]),
        "prop_id":          row["prop_id"],
        "property_class":   row["property_class"],
        "property_type":    row["property_type"],
        "ownership_type":   row["ownership_type"],
        "description":      row["description"],
        "land_use":         row["land_use"],
        "address":          row["address"],
        "city":             row["city"],
        "legal_description":row["legal_description"],
        "subdivision":      row["subdivision"],
        "site_area":        row["site_area"],
        "site_units":       row["site_units"],
        "bldg_area":        row["bldg_area"],
        "bldg_units":       row["bldg_units"],
        "sale_price":       row["sale_price"],
        "sale_date":        row["sale_date"],
        "sale_year":        row["sale_year"],
        "unit_price":       row["unit_price"],
        "unit_measure":     row["unit_measure"],
        "price_per_door":   row["price_per_door"],
        "price_per_acre":   row["price_per_acre"],
        "cap_rate":         row["cap_rate"],
        "total_units":      row["total_units"],
        "year_built":       row["year_built"],
        "related_party":    bool(row["related_party"]),
        "vendor_entity":    row["vendor_entity"],
        "vendor_person":    row["vendor_person"],
        "vendor_role":      row["vendor_role"],
        "vendor_type":      row["vendor_entity_type"],
        "purchaser_entity": row["purchaser_entity"],
        "purchaser_person": row["purchaser_person"],
        "purchaser_role":   row["purchaser_role"],
        "purchaser_type":   row["purchaser_entity_type"],
        "vendor_can":       row["vendor_can"],
        "purchaser_can":    row["purchaser_can"],
        "vendor_is_et_al":  row["vendor_is_et_al"],
        "purchaser_is_et_al": row["purchaser_is_et_al"],
    })

prices = [r["sale_price"] for r in txn_records if r["sale_price"]]
dashboard_data = {
    "transactions": txn_records,
    "filter_options": {
        "property_classes": sorted(gettel_txns["property_class"].dropna().unique().tolist()),
        "property_types":   sorted(gettel_txns["property_type"].dropna().unique().tolist()),
        "ownership_types":  sorted(gettel_txns["ownership_type"].dropna().unique().tolist()),
        "land_use_classes": sorted([v for v in gettel_txns["land_use"].dropna().unique().tolist() if v]),
        "cities":           sorted(gettel_txns["city"].dropna().unique().tolist()),
        "years":            sorted([int(y) for y in gettel_txns["sale_year"].dropna().unique() if y]),
        "subdivisions":     sorted(gettel_txns["subdivision"].dropna().unique().tolist()),
    },
    "kpis": {
        "total_transactions":   len(txn_records),
        "total_volume":         sum(prices),
        "avg_deal_size":        sum(prices)/len(prices) if prices else 0,
        "median_deal_size":     float(pd.Series(prices).median()) if prices else 0,
        "unique_companies":     len(set(gettel_txns["vendor_entity"].tolist() + gettel_txns["purchaser_entity"].tolist())),
        "unique_persons":       len(set(gettel_txns["vendor_person"].tolist() + gettel_txns["purchaser_person"].tolist()) - {""}),
        "cores_matched_companies": len([v for v in vendor_cans.values() if v] + [v for v in purchaser_cans.values() if v]),
    }
}

with open("dashboard_data.json","w",encoding="utf-8") as f:
    json.dump(dashboard_data, f, default=str)
print(f"  dashboard_data.json: {len(txn_records)} transactions")

# ── 1F: SCRAPE LIST ───────────────────────────────────────────────────────────

print("Building gettel_scrape_list.csv...")

entity_txn_count = defaultdict(int)
for _, row in gettel_txns.iterrows():
    for side in ["vendor","purchaser"]:
        ent   = row[f"{side}_entity"]
        etype = row[f"{side}_entity_type"]
        can   = row[f"{side}_can"]
        if ent and etype == "company" and not can:
            entity_txn_count[ent] += 1

scrape_rows = []
for ent, cnt in entity_txn_count.items():
    norm = normalize(ent)
    prov = detect_province(ent)
    if prov in ("BC","ON","OTHER"):
        continue
    priority = "high" if cnt >= 5 else ("medium" if cnt >= 2 else "low")
    scrape_rows.append({
        "entity_name":     ent,
        "normalized_name": norm,
        "txn_count":       cnt,
        "entity_type":     "company",
        "province_guess":  prov,
        "priority":        priority,
    })

scrape_df = pd.DataFrame(scrape_rows).sort_values("txn_count", ascending=False)
scrape_df.to_csv("gettel_scrape_list.csv", index=False)
print(f"  Scrape list: {len(scrape_df)} companies")
print(f"    High priority (5+ txns): {(scrape_df.priority=='high').sum()}")
print(f"    Medium priority (2-4 txns): {(scrape_df.priority=='medium').sum()}")
print(f"    Low priority (1 txn): {(scrape_df.priority=='low').sum()}")

# ── 1G: SAVE PARSED TRANSACTIONS ─────────────────────────────────────────────

gettel_txns.to_csv("gettel_transactions_parsed.csv", index=False)
print("\nAll outputs saved:")
print("  graph_data.json")
print("  dashboard_data.json")
print("  gettel_scrape_list.csv")
print("  gettel_transactions_parsed.csv")
