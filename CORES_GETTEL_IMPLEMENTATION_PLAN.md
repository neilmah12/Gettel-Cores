# CORES + GETTEL Integration — Implementation Plan

> For Sonnet to execute in Google Colab. Each block is one cell. Copy-paste ready.
> Generated: March 9, 2026. Based on analysis of actual data files.

---

## Data Profile (Measured)

### Gettel Excel: `2026_02_19_Gettel_Sales_2018-2026_-with_links.xlsx`

- **12,723 transactions**, 27 columns, sheet name `Sheet5`
- Years: 2018–2026 (last ~10 rows have `=YEAR()` formulas — use `data_only=True` to resolve)
- Property Classes: Commercial, Industrial, Institutional, Multi-Family, Residential, Special-Purpose, Urban Development/Agricultural
- Property Types: Building, Land
- Ownership Types: Investment, Owner/User (one lowercase "investment" variant — normalize)
- Cities: 116 unique (Edmonton, Calgary dominant)
- Sale Prices: $3,565 — $1.216B, median $1.4M, mean $4.27M
- **17,049 unique company entities** across Vendor + Purchaser
- **16,135 unique person names** embedded in Vendor/Purchaser fields
- 83.2% of Vendors have embedded director/shareholder info (multi-line)
- 90.0% of Purchasers have embedded director/shareholder info
- 871 "Et al" entries (multi-party transactions)

### Vendor/Purchaser Field Structure (Critical for Parsing)

The field is a multi-line string with this structure:
```
Line 1: Entity name (company or individual)
Line 2: Role line (optional)
Line 3: Person name (optional, if role line exists)
Line 4+: Address (optional, one or more lines)
```

#### Role Line Patterns (Measured Frequencies)
| Pattern | Count | Notes |
|---------|-------|-------|
| `Director:` | 14,476 | Standard — role on own line, name on next line |
| `Shareholder:` | 5,740 | Standard |
| `Shareholder;` | 157 | Semicolon variant — treat same as colon |
| `Director;` | 18 | Semicolon variant |
| `Directors:` | 16 | Plural — treat same as singular |
| `Director` (no colon) | 14 | Missing colon — match on keyword alone |
| `Shareholder` (no colon) | 7 | Missing colon |
| `Shareholders:` | 3 | Plural |
| `Director: [NAME]` | ~8 | Name on SAME line as role (e.g., `Director: Dan Sander`) |
| `Director:[NAME]` | ~3 | No space after colon (e.g., `Director:Gojko Trutina`) |
| `Director/Shareholder:` | 1 | Dual role |
| `Dshareholder:` | 1 | Typo |

#### Edge Cases to Handle
1. **No role line, multi-line = individual with address**: e.g., `"Vedran Jakovljevic\nBox 2017, Edmonton,AB T5M 0T2"` — entity IS the person, no company
2. **"Et,al" / "et al" suffix on entity name**: e.g., `"BKM Alliance Ltd.  Et,al"` — strip from company name, flag as multi-party
3. **"&" in entity names**: Distinguish company names containing "&" (e.g., `"C&H Properties Inc."`) from multiple individuals (e.g., `"Nizar & Shamim Merani"`) — rule: if line contains corp keywords → company name with "&"; otherwise → multiple individuals
4. **Person name on same line as role**: Regex must capture `Director:\s*(\S.+)` on one line
5. **Government/institutional entities**: `"THE CITY OF EDMONTON"`, `"ALBERTA INFRASTRUCTURE"` — tag as `entity_type = "government"`, skip CORES scraping
6. **B.C. / Ontario / out-of-province companies**: `"0777334 B.C. Ltd"`, `"Minto Properties Inc."` — cannot scrape from Alberta CORES, tag as `entity_type = "out_of_province"`

### Gettel Columns Reference

| Col Index | Name | Type | Use |
|-----------|------|------|-----|
| 0 | Home Path | str | Skip (internal Box path) |
| 1 | &Home | formula | Skip |
| 2 | Link | formula | Skip (View PDF hyperlink) |
| 3 | Prop ID | formula→str | **Keep** — extract number from HYPERLINK formula or use `data_only=True` |
| 4 | Property Class | str | **Filter** |
| 5 | Property Type | str | **Filter** |
| 6 | Ownership Type | str | **Filter** (normalize case) |
| 7 | Description | str | **Display** |
| 8 | Land Use Class | str | **Display** |
| 9 | Address | str | **Display** |
| 10 | City | str | **Filter** |
| 11 | Vendor | str (multi-line) | **Parse** → vendor_company, vendor_person, vendor_role |
| 12 | Purchaser | str (multi-line) | **Parse** → purchaser_company, purchaser_person, purchaser_role |
| 13 | Legal Description | str | **Display** |
| 14 | Subdivision | str | **Filter** |
| 15 | Site Area | float | **Display** |
| 16 | Site Units | str | **Display** (Acres, Sq Ft) |
| 17 | Bldg Area | float | **Display** |
| 18 | Bldg Units | str | **Display** |
| 19 | Sale Price | float | **Filter + Display** |
| 20 | Sale Date | datetime | **Filter + Display** |
| 21 | Sale Year | int | **Filter** |
| 22 | Unit Price | float | **Display** |
| 23 | Unit Measure | str | **Display** |
| 24 | Total Units | int | **Display** |
| 25 | Year Built | int | **Display** |
| 26 | PIDs | str | Skip |

### CORES Data (Current)

| File | Rows | Cols |
|------|------|------|
| `cores_companies_202603091457.csv` | 58 | 19 (no depth/parent_CAN) |
| `cores_directors_202603091457.csv` | 191 | 17 (no depth/parent_CAN) |
| `cores_companies_deep_202603091630.csv` | 25 | 21 (has depth, parent_CAN) |
| `cores_directors_deep_202603091630.csv` | 75 | 19 (has depth, parent_CAN) |
| **Total** | **83 companies, 266 director records** | |

Key stats: 123 unique individuals in CORES, 72 appear in 2+ companies. Top: Kyle Johnson (5 cos), Bryan Mar (4), David Rice (4), Ashley Rice (4).

### Transaction Frequency (Gettel)

| Txn Count | Entity Count |
|-----------|-------------|
| 1 | 16,571 |
| 2–5 | 2,517 |
| 6–10 | 142 |
| 11–20 | 74 |
| 21+ | 20 |

Top: City of Edmonton (140), City of Calgary (114), Mainstreet Equity (57), Boulevard RE Equities (42).

---

## Architecture: 4 Colab Blocks

```
Block 1: Data Preparation        → graph_data.json, dashboard_data.json, scrape_list.csv
Block 2: Mind Map HTML            → mindmap_section.html (reads graph_data.json)
Block 3: Dashboard HTML           → dashboard_section.html (reads dashboard_data.json)
Block 4: Assembly                 → cores_gettel_explorer.html (combines Blocks 2+3)
```

Each block is self-contained. Blocks 2 and 3 are independent. Block 4 joins them.

---

## Block 1: Data Preparation

**Colab Title:** `# 1 — DATA INGESTION & ENTITY RESOLUTION`

### Section 1A — Load Sources

**Inputs (upload to Colab):**
- `2026_02_19_Gettel_Sales_2018-2026_-with_links.xlsx`
- `cores_companies_202603091457.csv`
- `cores_directors_202603091457.csv`
- `cores_companies_deep_202603091630.csv`
- `cores_directors_deep_202603091630.csv`

**Operations:**
1. Read Gettel with `openpyxl`, `data_only=True` to resolve formulas (Prop ID, Sale Year)
2. Read 4 CORES CSVs with `pandas`
3. Normalize Phase 1 schema: add `depth=1`, `parent_CAN=""` columns
4. Concat: `all_companies = pd.concat([p1_cos, p2_cos])`, `all_directors = pd.concat([p1_dirs, p2_dirs])`
5. Build `cores_can_lookup`: dict mapping `normalized_name → CAN` for all 83 companies

**Name normalization function** (used everywhere):
```
normalize(name):
  - uppercase
  - strip whitespace
  - remove trailing periods
  - remove "Et,al" / "et al" suffixes
  - collapse multiple spaces
  - strip trailing/leading punctuation except parentheses
```

**Potential error:** Phase 1 CSVs have no `depth`/`parent_CAN` columns. Adding them with defaults must happen BEFORE concat. Pandas will fail silently if column names don't match — use `pd.concat(..., ignore_index=True)` and verify column count after.

### Section 1B — Parse Gettel Vendor/Purchaser

**Goal:** For each of the 12,723 rows, parse both Vendor (col 11) and Purchaser (col 12) into structured fields.

**Output DataFrame `gettel_txns`** — one row per transaction:

| Column | Source |
|--------|--------|
| txn_id | Auto-increment (0 to 12722) |
| prop_id | Col 3 (resolved) |
| property_class | Col 4 |
| property_type | Col 5 |
| ownership_type | Col 6 (title-cased) |
| description | Col 7 |
| land_use | Col 8 |
| address | Col 9 |
| city | Col 10 |
| legal_description | Col 13 |
| subdivision | Col 14 |
| site_area | Col 15 |
| site_units | Col 16 |
| bldg_area | Col 17 |
| bldg_units | Col 18 |
| sale_price | Col 19 |
| sale_date | Col 20 |
| sale_year | Col 21 |
| unit_price | Col 22 |
| unit_measure | Col 23 |
| year_built | Col 25 |
| vendor_raw | Col 11 (original) |
| vendor_entity | Parsed company/person name (line 1, cleaned) |
| vendor_entity_type | "company" / "individual" / "government" |
| vendor_person | Parsed person name from role line (or empty) |
| vendor_role | "Director" / "Shareholder" / "" |
| vendor_address | Parsed address lines joined |
| vendor_is_et_al | bool |
| purchaser_raw | Col 12 (original) |
| purchaser_entity | Same structure |
| purchaser_entity_type | |
| purchaser_person | |
| purchaser_role | |
| purchaser_address | |
| purchaser_is_et_al | bool |

**Parsing function `parse_party(raw_text)`:**

```
Input: "Jendrysek Holdings Ltd. \nShareholder:\nCharles Moe\n19-25012 Sturgeon Rd. Sturgeon County, AB  T8T 0C3"

Step 1: Split by \n, strip each line, remove empty lines
  → ["Jendrysek Holdings Ltd.", "Shareholder:", "Charles Moe", "19-25012 Sturgeon Rd. Sturgeon County, AB  T8T 0C3"]

Step 2: Line 0 = entity_name
  - Check for et al: regex r'\s*(Et,?\s*al\.?|et\s*al\.?)\s*$' → strip, set is_et_al=True
  - Classify entity_type:
    - If matches corp_keywords list → "company"
    - If matches r'^\d{5,}' (numbered corp) → "company"
    - If matches government list (CITY OF, PROVINCE OF, ALBERTA INFRASTRUCTURE, etc.) → "government"
    - Else → "individual"

Step 3: Find role line (lines 1+)
  - Regex on each line: r'^[Dd](irectors?|shareholder)[/Ss]?h?a?r?e?h?o?l?d?e?r?)?[;:]?\s*(.*)'
  - Simplified robust regex: r'(?i)^(directors?|shareholders?|director/shareholder|dshareholder)[;:]?\s*(.*?)$'
  - If role regex matches:
    - role = "Director" or "Shareholder" (normalized)
    - If capture group 2 is non-empty → person_name = group 2 (name on same line as role)
    - Else → person_name = next non-address line
  - If no role line but multi-line with entity_type="individual":
    - entity IS the person (vendor_person = vendor_entity, vendor_entity = "")
    - Remaining lines = address

Step 4: Remaining lines after entity + role + person = address
  - Join with ", "
  - Heuristic to detect address lines: starts with digit, or starts with Box/Suite/Unit/RR/PO, or contains province abbreviation pattern

Return: {entity, entity_type, person, role, address, is_et_al}
```

**Testing:** After parsing, print counts:
- entity_type distribution (company / individual / government)
- role distribution (Director / Shareholder / empty)
- is_et_al count
- rows where vendor_entity is empty (should be 0)
- rows where entity_type="company" but no person found (no embedded director info — this is fine, ~10% of records)

**Potential errors:**
- `Dshareholder:` (typo) — the regex must catch it → use fuzzy prefix matching
- `Director:l` (typo where name runs into colon) — capture group handles this
- Lines that look like addresses but are actually person names (e.g., a person named "1234 Some Name") — unlikely in practice but add validation: if "name" contains comma + province abbreviation → it's an address

### Section 1C — Entity Matching (Gettel ↔ CORES)

**Goal:** Link Gettel entities to CORES CAN numbers.

**Company matching:**

1. Build `cores_name_to_can` from `all_companies` DataFrame: `{normalize(Legal_Name): CAN}`
2. For each unique `vendor_entity` and `purchaser_entity` where `entity_type == "company"`:
   - Try exact match: `normalize(entity) in cores_name_to_can`
   - If no exact match, try without trailing punctuation / "LTD" vs "LTD." normalization
   - Assign `match_confidence = "exact"` or `"normalized"` or `"unmatched"`
3. Output: `company_match` dict: `{gettel_entity_name: {can: "...", confidence: "...", cores_name: "..."}}`

**Person matching (Gettel ↔ CORES):**

Strategy uses TWO layers with confidence levels:

| Confidence | Rule | Example |
|------------|------|---------|
| `high_direct` | Person named in Gettel Vendor/Purchaser AND that company matches a CORES company AND person exists as director/shareholder of that CORES company | Gettel: "Jendrysek Holdings → Charles Moe" + CORES: Jendrysek Holdings has director Charles Moe |
| `medium_cores` | Person exists as CORES director of a company that transacted in Gettel, but they weren't the named person in Gettel | CORES: John Smith is director of ABC Ltd. Gettel: ABC Ltd sold a property, but Gettel shows "Director: Jane Doe" |
| `low_name` | Person name from Gettel matches a CORES director name (Last, First) but the companies don't match | Same name, different company — could be same person or coincidence |

Implementation:
1. From `all_directors` where `Individual_or_Corp == "Individual"`, build `cores_person_lookup`: `{(LAST, FIRST): [{can, company_name, role, city, ...}]}`
2. From `gettel_txns`, for each parsed person (vendor_person, purchaser_person):
   - Split into (last, first) — heuristic: last word = last name, rest = first name (since Gettel format is "First Last", not "Last, First")
   - **IMPORTANT:** Gettel person names are "Charles Moe" (First Last). CORES directors are stored as separate Last_Name/First_Name. Matching needs to handle this.
   - Lookup `(MOE, CHARLES)` in `cores_person_lookup`
   - If found AND the associated CAN matches the Gettel company → `high_direct`
   - If found but CAN doesn't match → `low_name`
3. For all CORES directors whose company CAN matches a Gettel transacting company, but the director wasn't named in Gettel → `medium_cores`

**Output:** `person_edges` list of dicts, each with: `{person_name, person_key, company_can, txn_id, confidence, role}`

**Potential errors:**
- Gettel has "Frederick Li" but CORES has "FREDERICK" + "LI" — straightforward split works
- Gettel has "Marie-Josee Turmel" — first name = "Marie-Josee", last name = "Turmel" → works
- Gettel has "Amritpal Bindra" — works
- Gettel person name missing (only company, no director line) — skip, no person edge
- CORES has corporate shareholders (Individual_or_Corp = "Legal Entity") — these are company-to-company edges, not person edges

### Section 1D — Build Graph Data (for Mind Map)

**Output:** `graph_data.json` — structure matching Block 2 expectations.

The mind map needs to show:
- **Company nodes** (from CORES + Gettel)
- **Person nodes** (from CORES directors + Gettel parsed persons)
- **Transaction edges** (company → transaction as buyer/seller)
- **Ownership edges** (company → person/company as director/shareholder, from CORES)
- **Transaction-Person indirect edges** (person → transaction, via their company)

**JSON structure:**

```json
{
  "company_info": {
    "<CAN or entity_key>": {
      "can": "...",
      "label": "...",
      "status": "...",
      "depth": 1,
      "city": "...",
      "le_type": "...",
      "corp_type": "...",
      "registration_date": "...",
      "address": "...",
      "email": "...",
      "agent": "...",
      "last_ar_year": "...",
      "last_ar_filed": "...",
      "source": "cores" | "gettel_only",
      "children": [
        {
          "id": "person_key",
          "label": "LAST, First",
          "node_type": "person" | "company" | "other",
          "role": "Director" | "Shareholder",
          "pct_shares": "50",
          "status": "Active",
          "appointment": "2020/01/15",
          "address": "...",
          "source": "cores"
        }
      ],
      "transactions": [
        {
          "txn_id": 0,
          "role": "vendor" | "purchaser",
          "sale_price": 1500000,
          "sale_date": "2021-03-15",
          "property_class": "Commercial",
          "description": "Office: Suburban",
          "address": "11024 127 St",
          "city": "Edmonton",
          "counterparty": "Other Company Name"
        }
      ]
    }
  },
  "company_list": [
    {
      "can": "...",
      "label": "...",
      "status": "...",
      "depth": 1,
      "city": "...",
      "child_count": 5,
      "txn_count": 3,
      "source": "cores" | "gettel_only"
    }
  ],
  "person_index": {
    "<person_key>": {
      "label": "MOE, CHARLES",
      "companies": ["CAN1", "CAN2"],
      "transactions": [
        {"txn_id": 5, "confidence": "high_direct", "company_can": "CAN1", "role": "vendor"}
      ]
    }
  },
  "meta": {
    "total_companies": 83,
    "total_persons": 123,
    "total_transactions": 12723,
    "generated": "2026-03-09"
  }
}
```

**Key decision: which companies get into `company_info`?**
- **ALL companies go into `company_info` — no filters, no thresholds.** The pipeline must work identically whether the input is 50 companies or 17K. The user will feed smaller Gettel subsets and/or scrape CORES in chunks, so any hardcoded limit would break the workflow.
- CORES companies → full detail (status, registration, directors, address, etc.)
- Gettel companies that match CORES → merged (CORES detail + Gettel transactions)
- Gettel companies NOT in CORES → included with `source: "gettel_only"`, minimal info (just name, transactions)
- `company_list` is a lightweight array derived FROM `company_info` (not a separate subset) — it's just a summary view for the sidebar

**Performance note:** With the full 17K-company Gettel file, the JSON will be ~10–20 MB and the final HTML ~25–40 MB. This is fine for local use — browsers handle it. If a specific run produces a file that's slow to open, the user can pre-filter the Gettel Excel to a subset before running Block 1. The code itself never filters.

**For companies without CORES data (gettel_only):**
- `children` = persons parsed from Gettel (the one director/shareholder shown per transaction) — note: same person may appear multiple times across transactions, deduplicate
- `transactions` = all their Gettel deals
- No depth, no parent_CAN, no status, no registration info

### Section 1E — Build Dashboard Data

**Output:** `dashboard_data.json`

```json
{
  "transactions": [
    {
      "txn_id": 0,
      "prop_id": "26187",
      "property_class": "Industrial",
      "property_type": "Building",
      "ownership_type": "Investment",
      "description": "Warehouse: Multi-Bay",
      "land_use": "BI",
      "address": "145 McMillan Road",
      "city": "Fort McMurray",
      "subdivision": "Fort McMurray",
      "site_area": 1.1,
      "site_units": "Acres",
      "bldg_area": 16880,
      "bldg_units": "Sq Ft",
      "sale_price": 3750000,
      "sale_date": "2018-12-17",
      "sale_year": 2018,
      "unit_price": 222.16,
      "year_built": 2007,
      "vendor_entity": "First West Properties Corp.",
      "vendor_person": "Monty Balderston",
      "vendor_role": "Director",
      "vendor_type": "company",
      "purchaser_entity": "Global Advisory Services Inc",
      "purchaser_person": "",
      "purchaser_role": "",
      "purchaser_type": "company",
      "vendor_can": "2017172236",
      "purchaser_can": "",
      "vendor_is_et_al": false,
      "purchaser_is_et_al": false
    }
  ],
  "filter_options": {
    "property_classes": ["Commercial", "Industrial", ...],
    "property_types": ["Building", "Land"],
    "ownership_types": ["Investment", "Owner/User"],
    "cities": ["Edmonton", "Calgary", ...],
    "years": [2018, 2019, ...],
    "subdivisions": [...]
  },
  "kpis": {
    "total_transactions": 12723,
    "total_volume": 54347000000,
    "avg_deal_size": 4273079,
    "median_deal_size": 1400000,
    "unique_companies": 17049,
    "unique_persons": 16135,
    "cores_matched_companies": 83
  }
}
```

### Section 1F — Generate Scrape List

**Output:** `gettel_scrape_list.csv`

For companies in Gettel that are NOT yet in CORES and appear to be Alberta-registered:

| Column | Description |
|--------|-------------|
| entity_name | Company name as it appears in Gettel |
| normalized_name | After normalization |
| txn_count | Number of Gettel transactions |
| entity_type | "company" |
| province_guess | "AB" / "BC" / "ON" / "unknown" |
| priority | "high" (5+ txns) / "medium" (2-4) / "low" (1) |

Province detection rules:
- Contains "Alberta" or matches `r'^\d+\s+Alberta'` → AB
- Contains "B.C." or "BC " or "British Columbia" → BC
- Contains "Ontario" or "Ont." → ON
- Government entities (City of...) → skip
- Otherwise → unknown (likely AB if transacting in Alberta)

Sort by txn_count descending. This CSV becomes input for Phase 1 CORES scraper.

**Important:** Only include companies where `province_guess` is "AB" or "unknown" — BC/ON companies aren't in Alberta CORES.

### Section 1G — Save All Outputs

```python
# Save JSON files
with open('graph_data.json', 'w') as f:
    json.dump(graph_data, f)

with open('dashboard_data.json', 'w') as f:
    json.dump(dashboard_data, f)

# Save scrape list
scrape_df.to_csv('gettel_scrape_list.csv', index=False)

# Save parsed transactions (for future use)
gettel_txns.to_csv('gettel_transactions_parsed.csv', index=False)

# Print summary
print(f"Graph data: {len(graph_data['company_info'])} companies, {len(graph_data['person_index'])} persons")
print(f"Dashboard data: {len(dashboard_data['transactions'])} transactions")
print(f"Scrape list: {len(scrape_df)} companies to scrape")
print(f"  High priority (5+ txns): {len(scrape_df[scrape_df.priority == 'high'])}")
print(f"  Medium priority (2-4 txns): {len(scrape_df[scrape_df.priority == 'medium'])}")
```

---

## Block 2: Mind Map

**Colab Title:** `# 2 — NETWORK MIND MAP (HTML)`

**Reads:** `graph_data.json`
**Outputs:** `mindmap_section.html`

### Design Pattern

Follow the existing CORES Network Explorer (Block 2 v2 code provided as reference). Same visual language:
- DM Sans / DM Mono fonts
- Black/white/grey palette
- Sidebar with company list + filters
- Central canvas with D3 tree/graph
- Right detail panel on click

### Key Differences from Existing Block 2

1. **Same horizontal collapsible tree** — identical UX to the reference code. Company → directors/shareholders as child nodes. Sub-companies expandable/collapsible. No separate "transaction view" or force layout.
2. **Transactions in the detail panel** — when a company node is clicked, the right detail panel shows CORES info (registration, members) AND a "Transactions" section listing all Gettel deals for that company. Transactions are NOT nodes in the tree — they're data in the panel.
3. **Person cross-referencing**: In the sidebar, add a "People" tab below the "Companies" tab. Lists all persons from `person_index`. Clicking a person highlights ALL companies they're connected to in the sidebar, and shows their transaction history in the detail panel.
4. **Source badges**: Companies from CORES show a "CORES" badge. Gettel-only companies show "GETTEL". Companies with both show "CORES + GETTEL".
5. **Transaction count badge on tree nodes**: Each company node in the tree shows a small number indicating how many Gettel transactions it has (if any). This lets the user see at a glance which parts of the ownership tree are active in the market.

### HTML Structure

```
<div id="mindmap-tab">
  <header> ... (same style) </header>
  <div class="app">
    <div class="sb">
      <!-- Tab buttons: Companies | People -->
      <div class="sb-tabs">
        <button class="sb-tab active" data-tab="companies">Companies</button>
        <button class="sb-tab" data-tab="people">People</button>
      </div>
      <!-- Filters section (changes based on active tab) -->
      <div class="sb-filters" id="company-filters">
        <input id="f-co" placeholder="Search company...">
        <select id="f-city">...</select>
        <select id="f-status">...</select>
        <select id="f-source">All / CORES / Gettel Only</select>
        <select id="f-depth">...</select>
        <input id="f-min-txn" type="number" placeholder="Min transactions">
        <button class="btn-reset">Reset</button>
      </div>
      <div class="sb-filters" id="people-filters" style="display:none">
        <input id="f-person" placeholder="Search person...">
        <select id="f-role">All / Director / Shareholder</select>
        <input id="f-min-cos" type="number" placeholder="Min companies">
        <button class="btn-reset">Reset</button>
      </div>
      <!-- List -->
      <div class="sb-list" id="company-list">...</div>
      <div class="sb-list" id="people-list" style="display:none">...</div>
    </div>
    <div class="canvas">
      <svg id="tree-svg"></svg>
      <!-- Controls: zoom, fit, expand, collapse, export PNG -->
      <div class="ctrl-bar">...</div>
      <div class="legend">...</div>
    </div>
    <div class="detail" id="detail">
      <!-- Dynamic content based on selected node -->
    </div>
  </div>
</div>
```

### Horizontal Collapsible Tree (D3)

Same pattern as the reference Block 2 code. Re-use entirely:
- `buildHierarchy(can)` — recursive tree builder
- `collapsedNodes` Set for expand/collapse
- `d3.tree().nodeSize([34, 220])` layout
- `d3.linkHorizontal()` for edges
- Node styling: company depth colors, person white, other cream
- Click company node → toggle expand/collapse + show detail panel
- Click person/other node → show detail panel

Add to existing:
- **Transaction count badge** on company nodes (small monospace number to the right of the node label, e.g., `[3 txns]`) — only shown if company has Gettel transactions
- **Source indicator** (small dot on top-left of node circle: black = CORES, blue outline = Gettel-only, both = half-half)

### Detail Panel Content

**When company node clicked:**
```
[Company Name]
[Status badge] [Source badge] [Depth badge]

─── REGISTRATION (if CORES) ───
CAN: ...
Type: ...
Reg Date: ...
Last AR: ...

─── ADDRESS ───
Street, City, Province, Postal
Email

─── MEMBERS (if CORES) ───
[Director/Shareholder list with expand]

─── TRANSACTIONS (N) ───
[List of deals: date, price, buyer/seller, property class]
[Sorted by date descending]
[Each deal row is clickable — expands inline to show full detail:
  address, description, site/bldg area, unit price, year built,
  counterparty name + person + role]
```

**When person node clicked:**
```
[Person Name]
[Role] [Confidence badge]

─── COMPANIES (N) ───
[List of companies they're associated with]
[Click to navigate → selects that company in sidebar + draws its tree]

─── TRANSACTIONS (N) ───
[Transactions linked to this person]
[Grouped by confidence: high_direct first, then medium_cores]
[Each row shows: date, company, role (vendor/purchaser), price, property class]
```

### Performance Considerations

- `graph_data.json` scales with input — small CORES batch = small file, full 17K Gettel = ~15–20 MB. No code-level filtering; the user controls input size by choosing which files to upload.
- Sidebar list: use virtual scrolling (render only visible rows + buffer). With 17K companies, DOM rendering all at once would lag — render 100 rows, add more on scroll.
- D3 tree: no issue (tree is per-company, max ~50 nodes per tree view)
- Initial load: show empty canvas with "Select a company" message (same as existing)

---

## Block 3: Dashboard

**Colab Title:** `# 3 — TRANSACTION DASHBOARD (HTML)`

**Reads:** `dashboard_data.json`
**Outputs:** `dashboard_section.html`

### Layout

```
┌────────────────────────────────────────────────────────┐
│ HEADER: KPIs                                           │
│ [Total Txns] [Total Volume] [Avg Deal] [Matched COS]  │
├──────────┬─────────────────────────────────────────────┤
│ FILTERS  │ MAIN CONTENT                                │
│ (left)   │                                             │
│          │ ┌─────────────────────────────────────────┐ │
│ Property │ │ CHARTS ROW 1                            │ │
│ Class    │ │ [Volume by Year] [By Property Class]    │ │
│          │ ├─────────────────────────────────────────┤ │
│ Property │ │ CHARTS ROW 2                            │ │
│ Type     │ │ [Top Companies] [Top People]            │ │
│          │ ├─────────────────────────────────────────┤ │
│ Owner    │ │ TABLE                                   │ │
│ Type     │ │ [Searchable, sortable, paginated]       │ │
│          │ │ [Transaction list with all columns]     │ │
│ City     │ │                                         │ │
│          │ └─────────────────────────────────────────┘ │
│ Year     │                                             │
│ Range    │                                             │
│          │                                             │
│ Price    │                                             │
│ Range    │                                             │
│          │                                             │
│ Subdiv   │                                             │
│          │                                             │
│ Company  │                                             │
│ Search   │                                             │
│          │                                             │
│ Person   │                                             │
│ Search   │                                             │
│          │                                             │
│ [Reset]  │                                             │
└──────────┴─────────────────────────────────────────────┘
```

### Filters Panel (Left Sidebar)

All filters cross-filter: changing one updates all charts + table + KPIs.

| Filter | Type | Notes |
|--------|------|-------|
| Property Class | Multi-select checkboxes | 7 options |
| Property Type | Checkboxes | Building / Land |
| Ownership Type | Checkboxes | Investment / Owner-User |
| City | Searchable dropdown | 116 options, show top 20 + search |
| Year Range | Dual range slider | 2018–2026 |
| Price Range | Dual range slider | Log scale, $0 — $1.2B |
| Subdivision | Searchable dropdown | Many options |
| Company Search | Text input | Searches vendor_entity + purchaser_entity |
| Person Search | Text input | Searches vendor_person + purchaser_person |
| CORES Only | Checkbox | Show only transactions involving CORES-matched companies |
| Reset All | Button | Clears all filters |

### KPI Bar

Dynamic — updates with filters:
- **Transactions**: count of filtered rows
- **Total Volume**: sum of sale_price, formatted as $XB / $XM
- **Avg Deal Size**: mean of sale_price
- **CORES Matches**: count of filtered rows where vendor_can OR purchaser_can is non-empty

### Charts

**Library:** Chart.js v4 from CDN (`https://cdn.jsdelivr.net/npm/chart.js`) + `chartjs-plugin-zoom` (`https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom`). This gives interactive charts where the user can scroll-zoom on any axis, drag to pan, and pinch on mobile. Double-click resets zoom. All charts respond to cross-filtering.

**Chart.js global config to apply:**
```javascript
Chart.defaults.font.family = "'DM Sans', sans-serif";
Chart.defaults.color = '#1a1a1a';
Chart.defaults.plugins.zoom = {
  zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: 'x' },
  pan: { enabled: true, mode: 'x' }
};
```

**Chart 1 — Volume by Year (Stacked Bar)**
- X: year, Y: total sale_price
- Stacked by Property Class (one dataset per class, grey-scale palette)
- Zoom/pan on X axis to focus on a year range
- Tooltip shows: year, class, volume, txn count

**Chart 2 — By Property Class (Doughnut)**
- Segments by property_class
- Shows count + % of total volume in tooltip
- No zoom needed (static ring)

**Chart 3 — Top 20 Most Active Companies (Horizontal Bar)**
- Count of transactions per entity (vendor + purchaser combined)
- Show company name + bar + count
- Color-code: black if CORES-matched, grey if Gettel-only
- Zoom on Y axis to scroll through long list; user can also drag-resize the chart container height

**Chart 4 — Top 20 Most Connected People (Horizontal Bar)**
- People who appear in most transactions (as vendor_person or purchaser_person)
- Show person name + bar + count + number of distinct companies
- Same zoom/pan as Chart 3

### Transaction Table

- Paginated: 50 rows per page
- Sortable by clicking column headers (sale_price, sale_date, city)
- Columns shown:

| Column | Width | Notes |
|--------|-------|-------|
| # | 40px | Row number |
| Date | 80px | sale_date formatted |
| City | 90px | |
| Class | 80px | property_class abbreviated |
| Type | 60px | Building/Land |
| Description | 150px | Truncated with tooltip |
| Vendor | 150px | vendor_entity (highlight if CORES-matched) |
| Purchaser | 150px | purchaser_entity |
| Price | 100px | Formatted $X.XM |
| $/Unit | 70px | unit_price formatted |
| Area | 70px | bldg_area or site_area |

- Clicking a row → expands inline detail (all fields)
- Optional: "Export filtered CSV" button

### Implementation Notes

- Charts rendered via Chart.js (CDN). Two script tags in `<head>`: `chart.js` + `chartjs-plugin-zoom`
- All data embedded as JSON in the HTML (same pattern as Block 2)
- Cross-filtering uses a central `applyFilters()` function that:
  1. Reads all filter states
  2. Filters the transactions array
  3. Updates KPIs
  4. Calls `.update()` on each Chart.js instance with new data
  5. Re-renders table page 1
- For 12K rows, filtering is fast in JS (< 50ms with simple array filter)
- Table pagination: store filtered array, slice for current page
- Each chart lives in a `<div>` with `resize: vertical; overflow: auto` CSS so the user can drag-resize the container height

### Style

Same design language as mind map:
- DM Sans / DM Mono fonts
- Black/white/grey palette
- Minimal borders, clean spacing
- Monochromatic charts (shades of grey/black) with one accent color for CORES-matched items

---

## Block 4: HTML Assembly

**Colab Title:** `# 4 — ASSEMBLE FINAL HTML`

**Reads:** `mindmap_section.html`, `dashboard_section.html`
**Outputs:** `cores_gettel_explorer.html`

### Structure

```html
<!DOCTYPE html>
<html>
<head>
  <title>CORES + GETTEL Explorer</title>
  <!-- Shared fonts + base styles -->
</head>
<body>
  <!-- TOP NAV: Two tabs -->
  <nav class="top-nav">
    <button class="nav-tab active" data-tab="mindmap">Network Map</button>
    <button class="nav-tab" data-tab="dashboard">Dashboard</button>
  </nav>

  <!-- TAB CONTENT -->
  <div id="tab-mindmap" class="tab-content active">
    <!-- Injected from mindmap_section.html -->
  </div>
  <div id="tab-dashboard" class="tab-content" style="display:none">
    <!-- Injected from dashboard_section.html -->
  </div>

  <script>
    // Tab switching logic
    document.querySelectorAll('.nav-tab').forEach(btn => {
      btn.onclick = () => {
        document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
        btn.classList.add('active');
        document.getElementById('tab-' + btn.dataset.tab).style.display = 'block';
      };
    });
  </script>
</body>
</html>
```

### Assembly Logic (Python)

```
1. Read mindmap_section.html
2. Read dashboard_section.html
3. Extract <style> blocks from both → merge into shared <head>
4. Extract <script> blocks → ensure no variable name conflicts (namespace: MM_ for mindmap, DB_ for dashboard)
5. Extract <body> content → inject into tab containers
6. Add tab navigation
7. Add shared D3 CDN link (used by both)
8. Write final HTML
```

**Potential issues:**
- Both sections may define same CSS class names → namespace all classes: `.mm-sidebar` vs `.db-sidebar`
- Both sections import D3 → only include CDN once
- Dashboard uses Chart.js + chartjs-plugin-zoom → include CDN links once in shared `<head>`
- Tab switching must not re-initialize D3 or Chart.js (lazy init: only draw when tab becomes visible for the first time)
- JSON data for both sections must be in separate variables: `const MM_DATA = {...}` and `const DB_DATA = {...}`

**CDN dependencies (all in shared `<head>`):**
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom"></script>
```

### File Size Estimate

Scales with input. Examples:
- **Small batch** (100 companies, 500 txns): ~1–2 MB total → instant load
- **Medium batch** (2K companies, 5K txns): ~8–12 MB total → loads in 2–3s
- **Full Gettel** (17K companies, 12.7K txns): ~25–40 MB total → loads in 5–8s, fully usable
- HTML + CSS + JS overhead: ~50 KB (constant regardless of data size)
- If a specific run feels slow in browser: the user pre-filters the Gettel Excel before running Block 1. The code never truncates data.

---

## Execution Order

```
1. Upload 5 files to Colab
2. Run Block 1 → generates graph_data.json, dashboard_data.json, scrape_list.csv
3. Run Block 2 → generates mindmap_section.html
4. Run Block 3 → generates dashboard_section.html
5. Run Block 4 → generates cores_gettel_explorer.html → download
```

Each block has `# @title` annotation for Colab section headers.

---

## Future Iterations

1. **After scraping more companies**: Re-upload updated CORES CSVs + re-run Block 1. Blocks 2-4 remain unchanged.
2. **New Gettel export**: Upload new Excel, re-run Block 1. Same pipeline.
3. **Cross-tab communication (V2)**: Add event bus between mind map and dashboard — click company in dashboard → switches to mind map tab and selects it.
4. **Gettel PDF links**: The Prop ID column has hyperlinks to `database.gettelnetwork.com`. Could embed these as clickable links in the detail panel.
5. **Neo4j export**: Block 1 could also output Cypher import scripts for Neo4j if the dataset grows beyond what a browser can handle.
