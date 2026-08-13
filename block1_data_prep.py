# @title 1 — DATA INGESTION & ENTITY RESOLUTION
# Inputs: Gettel .xlsx + 4 CORES CSVs
# Outputs: graph_data.json, dashboard_data.json, gettel_scrape_list.csv, gettel_transactions_parsed.csv

import pandas as pd
import json
import re
import io
import os
from datetime import datetime
from collections import defaultdict
import openpyxl
from google.colab import files

# ── 1A: UPLOAD FILES ─────────────────────────────────────────────────────────

print("=" * 60)
print("UPLOAD REQUIRED — 5 files total")
print("=" * 60)
print()
print("Please upload the following files when prompted:")
print()
print("  1. Gettel Excel (the transaction database):")
print("     → 2026_02_19_Gettel_Sales_2018-2026_-with_links.xlsx")
print()
print("  2. CORES Phase 1 companies CSV:")
print("     → cores_companies_[timestamp].csv")
print()
print("  3. CORES Phase 1 directors CSV:")
print("     → cores_directors_[timestamp].csv")
print()
print("  4. CORES Phase 2 (deep) companies CSV:")
print("     → cores_companies_deep_[timestamp].csv")
print()
print("  5. CORES Phase 2 (deep) directors CSV:")
print("     → cores_directors_deep_[timestamp].csv")
print()
print("Select all 5 at once in the file picker (Ctrl+click / Cmd+click).")
print("=" * 60)

uploaded = files.upload()

if not uploaded:
    raise RuntimeError("No files uploaded. Re-run this cell and upload all 5 files.")

uploaded_names = list(uploaded.keys())
print(f"\nUploaded {len(uploaded_names)} file(s):")
for n in uploaded_names:
    print(f"  {n}")

# ── Match uploaded files by pattern ──────────────────────────────────────────

def find_file(pattern_keywords, uploaded_names, require=True):
    for name in uploaded_names:
        lower = name.lower()
        if all(kw in lower for kw in pattern_keywords):
            return name
    if require:
        raise FileNotFoundError(
            f"Could not find a file matching keywords {pattern_keywords} "
            f"among uploaded files: {uploaded_names}\n"
            f"Please re-run the cell and upload all 5 required files."
        )
    return None

gettel_file = find_file(['.xlsx'], uploaded_names)
p1_cos_file  = find_file(['companies', 'deep'], uploaded_names, require=False)
p1_dirs_file = find_file(['directors', 'deep'], uploaded_names, require=False)
# Phase 1 files must NOT contain 'deep'
p1_cos_file  = next((n for n in uploaded_names if 'companies' in n.lower() and 'deep' not in n.lower()), None)
p1_dirs_file = next((n for n in uploaded_names if 'directors' in n.lower() and 'deep' not in n.lower()), None)
p2_cos_file  = next((n for n in uploaded_names if 'companies' in n.lower() and 'deep' in n.lower()), None)
p2_dirs_file = next((n for n in uploaded_names if 'directors' in n.lower() and 'deep' in n.lower()), None)

missing = []
if not gettel_file:  missing.append("Gettel .xlsx")
if not p1_cos_file:  missing.append("cores_companies (Phase 1, no 'deep' in name)")
if not p1_dirs_file: missing.append("cores_directors (Phase 1, no 'deep' in name)")
if not p2_cos_file:  missing.append("cores_companies_deep (Phase 2)")
if not p2_dirs_file: missing.append("cores_directors_deep (Phase 2)")

if missing:
    raise FileNotFoundError(
        f"\nMissing files — could not identify:\n" +
        "\n".join(f"  - {m}" for m in missing) +
        f"\n\nUploaded: {uploaded_names}\n"
        f"Re-run the cell and upload all 5 files with the correct names."
    )

print(f"\nFile mapping:")
print(f"  Gettel      → {gettel_file}")
print(f"  P1 Companies→ {p1_cos_file}")
print(f"  P1 Directors→ {p1_dirs_file}")
print(f"  P2 Companies→ {p2_cos_file}")
print(f"  P2 Directors→ {p2_dirs_file}")

# ── 1A: LOAD SOURCES ─────────────────────────────────────────────────────────

print("\nLoading Gettel...")
wb = openpyxl.load_workbook(io.BytesIO(uploaded[gettel_file]), data_only=True)

# Auto-detect sheet name — falls back to first sheet if Sheet5 not found
sheet_name = "Sheet5" if "Sheet5" in wb.sheetnames else wb.sheetnames[0]
if sheet_name != "Sheet5":
    print(f"  Note: 'Sheet5' not found — using sheet '{sheet_name}'")
ws = wb[sheet_name]
rows = list(ws.iter_rows(values_only=True))
gettel_headers = rows[0]
gettel_raw = pd.DataFrame(rows[1:], columns=gettel_headers)
print(f"  Gettel: {len(gettel_raw)} rows, {len(gettel_raw.columns)} cols")

print("Loading CORES...")
p1_cos  = pd.read_csv(io.BytesIO(uploaded[p1_cos_file]),  dtype=str)
p1_dirs = pd.read_csv(io.BytesIO(uploaded[p1_dirs_file]), dtype=str)
p2_cos  = pd.read_csv(io.BytesIO(uploaded[p2_cos_file]),  dtype=str)
p2_dirs = pd.read_csv(io.BytesIO(uploaded[p2_dirs_file]), dtype=str)

p1_cos["depth"]      = "1"
p1_cos["parent_CAN"] = ""
p1_dirs["depth"]     = "1"
p1_dirs["parent_CAN"]= ""

all_companies = pd.concat([p1_cos, p2_cos], ignore_index=True)
all_directors = pd.concat([p1_dirs, p2_dirs], ignore_index=True)
print(f"  CORES (raw): {len(all_companies)} companies, {len(all_directors)} director records")

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

gettel_cols = list(gettel_raw.columns)

def get_col(row, idx):
    try:
        return row.iloc[idx]
    except:
        return None

print("Parsing Gettel vendor/purchaser fields...")
records = []
for i, row in gettel_raw.iterrows():
    vp = parse_party(get_col(row, 11))
    pp = parse_party(get_col(row, 12))

    sale_price = get_col(row, 19)
    try:
        sale_price = float(sale_price) if sale_price else None
    except:
        sale_price = None

    sale_date = get_col(row, 20)
    sale_date_str = sale_date.strftime('%Y-%m-%d') if hasattr(sale_date, 'strftime') else str(sale_date or '')

    sale_year = get_col(row, 21)
    try:
        sale_year = int(sale_year) if sale_year else None
    except:
        sale_year = None

    unit_price = get_col(row, 22)
    try:
        unit_price = float(unit_price) if unit_price else None
    except:
        unit_price = None

    site_area = get_col(row, 15)
    try:
        site_area = float(site_area) if site_area else None
    except:
        site_area = None

    bldg_area = get_col(row, 17)
    try:
        bldg_area = float(bldg_area) if bldg_area else None
    except:
        bldg_area = None

    year_built = get_col(row, 25)
    try:
        year_built = int(year_built) if year_built else None
    except:
        year_built = None

    ownership_type = str(get_col(row, 6) or '').strip().title()

    records.append({
        "txn_id":             i,
        "prop_id":            str(get_col(row, 3) or ''),
        "property_class":     str(get_col(row, 4) or ''),
        "property_type":      str(get_col(row, 5) or ''),
        "ownership_type":     ownership_type,
        "description":        str(get_col(row, 7) or ''),
        "land_use":           str(get_col(row, 8) or ''),
        "address":            str(get_col(row, 9) or ''),
        "city":               str(get_col(row, 10) or ''),
        "legal_description":  str(get_col(row, 13) or ''),
        "subdivision":        str(get_col(row, 14) or ''),
        "site_area":          site_area,
        "site_units":         str(get_col(row, 16) or ''),
        "bldg_area":          bldg_area,
        "bldg_units":         str(get_col(row, 18) or ''),
        "sale_price":         sale_price,
        "sale_date":          sale_date_str,
        "sale_year":          sale_year,
        "unit_price":         unit_price,
        "unit_measure":       str(get_col(row, 23) or ''),
        "year_built":         year_built,
        "vendor_raw":         str(get_col(row, 11) or ''),
        "vendor_entity":      vp["entity"],
        "vendor_entity_type": vp["entity_type"],
        "vendor_person":      vp["person"],
        "vendor_role":        vp["role"],
        "vendor_address":     vp["address"],
        "vendor_is_et_al":    vp["is_et_al"],
        "purchaser_raw":      str(get_col(row, 12) or ''),
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
        "subdivision":      row["subdivision"],
        "site_area":        row["site_area"],
        "site_units":       row["site_units"],
        "bldg_area":        row["bldg_area"],
        "bldg_units":       row["bldg_units"],
        "sale_price":       row["sale_price"],
        "sale_date":        row["sale_date"],
        "sale_year":        row["sale_year"],
        "unit_price":       row["unit_price"],
        "year_built":       row["year_built"],
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
