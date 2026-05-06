# CORES + GETTEL — Update Instructions (Patch v2)

> For Sonnet to apply to the existing Block 1–4 code files.
> Each section describes WHAT to change, WHERE in the code, and WHY.

---

## Update 1: Clickable Names in Top 20 People Chart → Filter Table

**Problem:** The Top 20 People horizontal bar chart shows person names, but clicking a bar does nothing. The user wants to click a person's name/bar and have the transaction table filter to show only that person's transactions.

**Affected file:** `block3_dashboard.py` (Block 3)

### What to change

**1A. Add a click handler to the People chart.**

In `updatePeopleChart()`, when creating the Chart.js instance (`new Chart(...)`), add an `onClick` handler in the options:

```javascript
options: {
  // ...existing options...
  onClick: (evt, elements) => {
    if (elements.length > 0) {
      const idx = elements[0].index;
      const personName = DB_charts.ppl.data.labels[idx];
      DB_filterByPerson(personName);
    }
  }
}
```

**1B. Create the `DB_filterByPerson` function.**

Add a new function that:
1. Sets the Person Search input (`db-f-person`) to the clicked person name
2. Calls `DB_applyFilters()` to re-filter everything
3. Scrolls the main area to the table

```javascript
window.DB_filterByPerson = function(name) {
  document.getElementById('db-f-person').value = name;
  DB_applyFilters();
  document.querySelector('.db-table-card').scrollIntoView({behavior:'smooth'});
};
```

**1C. Same for Top 20 Companies chart** — make company names clickable too.

In `updateCosChart()`, add the same pattern:
```javascript
onClick: (evt, elements) => {
  if (elements.length > 0) {
    const idx = elements[0].index;
    const fullName = DB_cosFullNames[idx]; // use full name, not truncated label
    document.getElementById('db-f-company').value = fullName;
    DB_applyFilters();
    document.querySelector('.db-table-card').scrollIntoView({behavior:'smooth'});
  }
}
```

Store the full (un-truncated) names in a module-level array `DB_cosFullNames` inside `updateCosChart()` so the click handler can access the real name (not the `slice(0,28)+'…'` label).

**1D. Visual feedback:** Change cursor to pointer on the chart bars. Add this CSS:

```css
#db-chart-cos, #db-chart-people { cursor: pointer; }
```

**1E. Add a "clear filter" indicator.** When the table is filtered by a chart click, show a small banner above the table:

```html
<div id="db-active-filter" style="display:none;padding:6px 12px;background:#f0efe8;border:1px solid #e0e0da;border-radius:4px;margin-bottom:8px;font-size:12px;display:flex;align-items:center;justify-content:space-between;">
  <span id="db-active-filter-text"></span>
  <button onclick="DB_clearChartFilter()" style="border:none;background:none;cursor:pointer;font-size:14px;">×</button>
</div>
```

`DB_clearChartFilter()` clears both company and person search inputs and re-applies filters.

---

## Update 2: Fix Top 20 Companies Chart (Bug)

**Problem:** The Top 20 Companies chart shows all companies with count = 1. The bars are the same tiny length.

**Root cause:** In `updateCosChart()` lines 382-383, the counter initialization is broken:

```javascript
// BROKEN — comma operator causes coCount[ve] to be assigned 0 (the number), not the object
if(ve) coCount[ve]=(coCount[ve]||{count:0,matched:!!t.vendor_can}).count++||0, coCount[ve].count++;
```

The expression `(obj).count++||0` evaluates to 0 (because count starts at 0, and `0++` returns 0, then `0||0` = 0), then assigns that 0 to `coCount[ve]`. On the next line, `coCount[ve].count++` fails silently because `coCount[ve]` is now the number 0, not an object.

**Affected file:** `block3_dashboard.py` (Block 3)

### What to change

Replace the entire `updateCosChart()` function body with a clean counter:

```javascript
function updateCosChart(){
  const coCount = {};
  DB_filtered.forEach(t => {
    if (t.vendor_entity) {
      if (!coCount[t.vendor_entity]) coCount[t.vendor_entity] = {count: 0, matched: false};
      coCount[t.vendor_entity].count++;
      if (t.vendor_can) coCount[t.vendor_entity].matched = true;
    }
    if (t.purchaser_entity) {
      if (!coCount[t.purchaser_entity]) coCount[t.purchaser_entity] = {count: 0, matched: false};
      coCount[t.purchaser_entity].count++;
      if (t.purchaser_can) coCount[t.purchaser_entity].matched = true;
    }
  });
  const sorted = Object.entries(coCount).sort((a,b) => b[1].count - a[1].count).slice(0, 20);
  DB_cosFullNames = sorted.map(e => e[0]);
  const labels = sorted.map(e => e[0].length > 30 ? e[0].slice(0,28) + '…' : e[0]);
  const data   = sorted.map(e => e[1].count);
  const colors = sorted.map(e => e[1].matched ? '#111' : '#aaa');

  // ... rest of chart creation (same as before, but add onClick handler per Update 1C)
}
```

Also declare `let DB_cosFullNames = [];` at the top of the script (next to `let DB_charts = {};`).

---

## Update 3: Add Prop ID to Table + Fix Address Display

**Problem:** 
- `prop_id` from Gettel is not shown in the transaction table. It's an important identifier for brokers.
- In the mind map transaction tooltips, the address should combine `address + city` for readability.

**Affected files:** `block3_dashboard.py` (Block 3) + `block2_mindmap.py` (Block 2)

### 3A. Add Prop ID column to the dashboard table

**In the `<thead>` row**, add a column after `#`:

```html
<th style="width:36px">#</th>
<th data-col="prop_id" onclick="DB_sort('prop_id')" style="width:60px">Prop ID</th>
<th data-col="sale_date" onclick="DB_sort('sale_date')">Date</th>
<!-- ...rest unchanged... -->
```

**In `renderTable()`**, add the prop_id cell after the row number:

```javascript
tr.innerHTML=`
  <td>${n}</td>
  <td style="font-family:'DM Mono',monospace;font-size:11px">${t.prop_id||'—'}</td>
  <td>${t.sale_date||'—'}</td>
  <!-- ...rest unchanged... -->
`;
```

**In the expanded detail row**, also show Prop ID:

```javascript
det.innerHTML=`<td colspan="12"><div class="db-detail-grid">
  <div class="db-detail-row"><span class="dl">Prop ID</span><span class="dv">${t.prop_id||'—'}</span></div>
  <div class="db-detail-row"><span class="dl">Address</span><span class="dv">${[t.address, t.city].filter(Boolean).join(', ')||'—'}</span></div>
  <!-- ...rest unchanged... -->
</div></td>`;
```

Note: update the `colspan` from 11 to 12 since we added a column.

**In `DB_exportCSV()`**, add `prop_id` to the cols array (first position after txn_id):

```javascript
const cols = ['txn_id','prop_id','sale_date','city', ...rest... ];
```

### 3B. Fix address display in mind map transaction tooltips

**In `block2_mindmap.py`**, in the `showCompanyDetail()` function where transactions are rendered, change the address display from:

```javascript
<div class="d-row"><span class="lbl">Address</span><span class="val">${t.address||'—'}</span></div>
```

to:

```javascript
<div class="d-row"><span class="lbl">Address</span><span class="val">${[t.address, t.city].filter(Boolean).join(', ')||'—'}</span></div>
```

### 3C. Add Prop ID to mind map transaction detail

In the same `showCompanyDetail()` function, add Prop ID as the first row in the transaction detail expandable section:

```javascript
<div class="txn-detail" id="txn-${i}-${can}">
  <div class="d-row"><span class="lbl">Prop ID</span><span class="val">${t.prop_id||'—'}</span></div>
  <div class="d-row"><span class="lbl">Address</span><span class="val">${[t.address, t.city].filter(Boolean).join(', ')||'—'}</span></div>
  <!-- ...rest unchanged... -->
</div>
```

### 3D. Pass `prop_id` to graph_data.json transactions

**In `block1_data_prep__1_.py`**, in Section 1D where `txns_by_can` is built (around line 459), add `prop_id` to the entry dict:

```python
entry = {
    "txn_id":         int(row["txn_id"]),
    "prop_id":        row["prop_id"],            # ADD THIS
    "sale_price":     row["sale_price"],
    # ...rest unchanged...
}
```

Also do the same for the gettel-only company transaction entries (around line 548):

```python
t_entry = {
    "txn_id":         int(row["txn_id"]),
    "prop_id":        row["prop_id"],            # ADD THIS
    "sale_price":     row["sale_price"],
    # ...rest unchanged...
}
```

### 3E. Fix the `bldg_units` field in mind map transactions

Currently `block1_data_prep__1_.py` passes `bldg_area` and `unit_price` to graph_data.json transactions but NOT `bldg_units` or `site_units`. Add these to the entry dict:

```python
entry = {
    # ...existing fields...
    "bldg_area":      row["bldg_area"],
    "bldg_units":     row["bldg_units"],          # ADD THIS
    "site_area":      row["site_area"],
    "site_units":     row["site_units"],           # ALREADY EXISTS, just verify
    # ...
}
```

---

## Update 4: CRE Broker Perspective — Additional Metrics & Features

**Context:** The user is a CRE broker focused on Office, Multi-Family, and Industrial. These additions surface insights that directly support deal-making.

### 4A. Add $/SF calculation and display (critical for Office + Industrial)

**Block 3 — Dashboard table:** The `$/Unit` column already exists but may show the raw Gettel unit_price. Verify it's displayed correctly. Additionally, for rows where `bldg_area > 0` and `sale_price > 0`, calculate an implied $/SF if `unit_price` is missing:

In `renderTable()`, change the $/Unit cell from:
```javascript
<td class="db-price">${t.unit_price?fmtPrice(t.unit_price):'—'}</td>
```
to:
```javascript
<td class="db-price">${formatPSF(t)}</td>
```

New helper function:
```javascript
function formatPSF(t) {
  if (t.unit_price) return fmtPrice(t.unit_price);
  if (t.sale_price && t.bldg_area && parseFloat(t.bldg_area) > 0) {
    const psf = parseFloat(t.sale_price) / parseFloat(t.bldg_area);
    return '$' + psf.toFixed(2) + '*';  // asterisk = calculated, not from source
  }
  return '—';
}
```

Add a footnote below the table: `* $/Unit calculated from Sale Price ÷ Bldg Area`

### 4B. Add Cap Rate proxy indicator (critical for Investment/MF)

For Investment properties, the `unit_price` relative to `bldg_area` gives a rough cap rate proxy when compared across similar assets. While we don't have NOI data, we can flag deals that are significantly above or below the average $/SF for their property class + city combination.

In `DB_applyFilters()`, after filtering, calculate average $/SF by (property_class, city):

```javascript
const avgPSF = {};
DB_filtered.forEach(t => {
  if (!t.bldg_area || !t.sale_price || parseFloat(t.bldg_area) <= 0) return;
  const key = (t.property_class||'') + '|' + (t.city||'');
  if (!avgPSF[key]) avgPSF[key] = {sum: 0, count: 0};
  avgPSF[key].sum += parseFloat(t.sale_price) / parseFloat(t.bldg_area);
  avgPSF[key].count++;
});
Object.keys(avgPSF).forEach(k => avgPSF[k].avg = avgPSF[k].sum / avgPSF[k].count);
DB_avgPSF = avgPSF;
```

Then in `renderTable()`, add a visual indicator (small dot or colored background) when a deal's $/SF is >20% above or below the average for its class+city. This helps spot undervalued or premium-priced assets.

### 4C. Add Year Built to the table (useful for all asset classes)

Currently `year_built` is only in the expanded detail row. For a broker, seeing the vintage at a glance matters (especially for Office — age affects class A/B/C classification).

Add a `Year Built` column to the main table after Area:

```html
<th data-col="year_built" onclick="DB_sort('year_built')">Built</th>
```

```javascript
<td>${t.year_built||'—'}</td>
```

Update `colspan` in the detail row accordingly.

### 4D. Add Ownership Type to the visible table

Currently `ownership_type` is only a filter and appears in the expanded detail. For a broker, knowing instantly if a deal is Investment vs Owner/User shapes how you interpret the price.

Add as a column:
```html
<th data-col="ownership_type" onclick="DB_sort('ownership_type')">Own</th>
```

Show abbreviated: "Inv" for Investment, "O/U" for Owner/User:
```javascript
<td>${t.ownership_type === 'Investment' ? 'Inv' : 'O/U'}</td>
```

### 4E. Add a "Deal Velocity" KPI

Add a new KPI card: **Deals/Month** — calculates the average number of transactions per month in the filtered date range. This tells a broker whether the market is accelerating or cooling.

```javascript
// In updateKPIs():
const dates = DB_filtered.map(t => new Date(t.sale_date)).filter(d => !isNaN(d));
let dealsPerMonth = 0;
if (dates.length >= 2) {
  const minDate = new Date(Math.min(...dates));
  const maxDate = new Date(Math.max(...dates));
  const months = (maxDate.getFullYear() - minDate.getFullYear()) * 12 + (maxDate.getMonth() - minDate.getMonth()) + 1;
  dealsPerMonth = (DB_filtered.length / months).toFixed(1);
}
document.getElementById('db-k-velocity').textContent = dealsPerMonth || '—';
```

Add the KPI card in the HTML:
```html
<div class="db-kpi"><div class="kv" id="db-k-velocity">—</div><div class="kl">Deals/Month</div></div>
```

### 4F. Add Vendor/Purchaser role column to table

Add a column showing whether each entity was a net buyer or seller. This helps spot patterns like "Company X has been aggressively selling office assets since 2023."

Instead of a separate column (table is already wide), **color-code the Vendor and Purchaser cells**:
- Vendor cell: subtle red-tinted background (`#fef5f5`)
- Purchaser cell: subtle green-tinted background (`#f5fef5`)

```css
.db-vendor-cell { background: #fef5f5; }
.db-purchaser-cell { background: #f5fef5; }
```

### 4G. Add Site Area (Acres) to visible table for Land deals

When `property_type === 'Land'`, `bldg_area` is usually 0 or empty. The Area column should show `site_area` + `site_units` for Land deals and `bldg_area` + `bldg_units` for Building deals.

The current code already does this:
```javascript
<td>${fmtArea(t.bldg_area||t.site_area, t.bldg_units||t.site_units)}</td>
```

But this falls back to site_area only if bldg_area is falsy. Improve to prioritize based on property_type:
```javascript
function smartArea(t) {
  if (t.property_type === 'Land') return fmtArea(t.site_area, t.site_units);
  if (t.bldg_area && parseFloat(t.bldg_area) > 0) return fmtArea(t.bldg_area, t.bldg_units);
  return fmtArea(t.site_area, t.site_units);
}
```

### 4H. Mind map — Show deal volume in company detail panel

In the mind map `showCompanyDetail()`, after listing transactions, add a summary line at the top of the Transactions section:

```javascript
const totalVol = txns.reduce((s,t) => s + (parseFloat(t.sale_price)||0), 0);
const buyCount = txns.filter(t => t.role === 'purchaser').length;
const sellCount = txns.filter(t => t.role === 'vendor').length;
html += `<div class="d-section">
  <div class="d-section-title">Transactions (${txns.length})</div>
  <div style="font-size:11px;color:var(--muted);margin-bottom:8px;">
    Total Volume: ${fmtPrice(totalVol)} · ${buyCount} buys · ${sellCount} sells
  </div>`;
```

---

## Summary of Changes by File

### `block1_data_prep__1_.py` (Block 1)
- Add `prop_id` to `txns_by_can` entry dict (Section 1D, ~line 459)
- Add `prop_id` to gettel-only company transaction entries (~line 548)
- Add `bldg_units` to `txns_by_can` entry dict

### `block2_mindmap.py` (Block 2)
- Fix address display: `[t.address, t.city].filter(Boolean).join(', ')` in transaction detail
- Add Prop ID row to transaction detail
- Add transaction volume summary (buy/sell count + total) above transaction list

### `block3_dashboard.py` (Block 3)
- **Fix** `updateCosChart()` counter bug (broken JS expression)
- Add click handlers to Top 20 People chart → filters table by person
- Add click handlers to Top 20 Companies chart → filters table by company
- Add `DB_filterByPerson()` and `DB_clearChartFilter()` functions
- Add active filter banner above table
- Add Prop ID column to table (after #)
- Add Year Built column to table
- Add Ownership Type column (abbreviated)
- Add `formatPSF()` helper with calculated $/SF fallback
- Add $/SF comparison indicator (above/below avg for class+city)
- Add Deals/Month KPI card
- Color-code Vendor/Purchaser cells (subtle red/green tint)
- Improve `smartArea()` function to prioritize by property_type
- Update `colspan` in detail rows (11 → 15 to match new column count)
- Update `DB_exportCSV()` cols array to include new fields
- Add `cursor: pointer` CSS to chart canvases
- Add footnote about calculated $/SF

### `block4_assembly.py` (Block 4)
- No changes needed. Assembly logic is agnostic to column count/chart handlers.

---

## Testing Checklist

After applying changes:
1. Run Block 1 → verify `prop_id` appears in `graph_data.json` transactions
2. Run Block 3 → verify Top 20 Companies chart shows correct counts (not all 1)
3. Click a person name in Top 20 People chart → table should filter to that person
4. Click a company in Top 20 Companies chart → table should filter to that company
5. Verify Prop ID column appears in dashboard table
6. Verify Address in mind map transaction tooltip shows "123 Street, Edmonton"
7. Verify $/SF calculated column shows `*` suffix when computed from price/area
8. Verify Year Built and Own columns appear in table
9. Verify Deals/Month KPI updates correctly with filters
10. Verify Vendor cells have subtle red tint, Purchaser cells subtle green tint
