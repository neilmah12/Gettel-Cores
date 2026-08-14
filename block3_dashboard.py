# @title 3 — TRANSACTION DASHBOARD (HTML)
# Input: dashboard_data.json
# Output: dashboard_section.html

import json

with open("dashboard_data.json","r",encoding="utf-8") as f:
    dashboard_data = f.read()

html = r"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

  #dashboard-tab{
    --surface-1:      #fcfcfb;
    --page-plane:     #f9f9f7;
    --text-primary:   #0b0b0b;
    --text-secondary: #52514e;
    --text-muted:     #898781;
    --grid-line:      #e1e0d9;
    --border:         rgba(11,11,11,0.10);
    --accent:         #2a78d6;
    --accent-2:       #1baf7a;
    --accent-3:       #eda100;
    --status-warn:    #fab219;
    --status-warn-ink:#7a5200;
    --delta-good:     #006300;
  }
  @media (prefers-color-scheme: dark) {
    #dashboard-tab{
      --surface-1:      #1a1a19;
      --page-plane:     #0d0d0d;
      --text-primary:   #ffffff;
      --text-secondary: #c3c2b7;
      --text-muted:     #898781;
      --grid-line:      #2c2c2a;
      --border:         rgba(255,255,255,0.10);
      --accent:         #3987e5;
      --accent-2:       #199e70;
      --accent-3:       #c98500;
      --status-warn:    #fab219;
      --status-warn-ink:#fde3ab;
      --delta-good:     #0ca30c;
    }
  }

  /* box-sizing only — NOT margin/padding:0. #dashboard-tab's ID specificity
     would outrank every plain-class rule below it (.db-kpi, .db-seg button,
     etc.) regardless of source order, silently zeroing their padding. Each
     component below sets its own spacing explicitly instead. */
  #dashboard-tab *{box-sizing:border-box;}
  #dashboard-tab h2, #dashboard-tab h4, #dashboard-tab summary{margin:0;}
  #dashboard-tab{font-family:'DM Sans',sans-serif;background:var(--page-plane);color:var(--text-primary);min-height:100vh;}

  .db-header{background:var(--surface-1);border-bottom:1px solid var(--border);padding:12px 20px;}
  .db-title-row{display:flex;align-items:center;gap:10px;margin-bottom:10px;}
  .db-header h2{font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;color:var(--text-secondary);}
  .db-badge{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:var(--accent);
    background:color-mix(in srgb, var(--accent) 14%, transparent);border:1px solid color-mix(in srgb, var(--accent) 35%, transparent);
    border-radius:20px;padding:3px 9px;}
  .db-kpis{display:flex;gap:16px;flex-wrap:wrap;}
  .db-kpi{background:var(--page-plane);border:1px solid var(--border);border-radius:6px;padding:8px 14px;min-width:120px;}
  .db-kpi .kv{font-size:20px;font-weight:600;font-family:'DM Mono',monospace;color:var(--text-primary);}
  .db-kpi .kl{font-size:11px;color:var(--text-secondary);margin-top:2px;}
  .db-kpi .kd{font-size:10px;color:var(--text-muted);margin-top:2px;font-family:'DM Mono',monospace;}

  .db-body{display:grid;grid-template-columns:240px 1fr;height:calc(100vh - 90px);}

  .db-sidebar{background:var(--surface-1);border-right:1px solid var(--border);overflow-y:auto;padding:10px 12px;}
  .db-fgroup{border:none;border-bottom:1px solid var(--grid-line);}
  .db-fgroup:last-of-type{border-bottom:none;}
  .db-fgroup summary{list-style:none;cursor:pointer;padding:9px 2px;font-size:11px;font-weight:600;
    text-transform:uppercase;letter-spacing:.05em;color:var(--text-secondary);display:flex;align-items:center;justify-content:space-between;}
  .db-fgroup summary::-webkit-details-marker{display:none;}
  .db-fgroup summary::after{content:'▸';font-size:10px;color:var(--text-muted);transition:transform .15s;}
  .db-fgroup[open] summary::after{transform:rotate(90deg);}
  .db-fgroup summary:hover{color:var(--text-primary);}
  .db-fgroup-body{padding:2px 2px 10px;}

  .db-cb-search{width:100%;padding:5px 7px;font-size:11px;font-family:inherit;border:1px solid var(--border);
    border-radius:4px;background:var(--page-plane);color:var(--text-primary);margin-bottom:6px;}
  .db-cb-actions{display:flex;gap:10px;margin-bottom:6px;}
  .db-cb-actions a{font-size:10px;color:var(--accent);cursor:pointer;text-decoration:none;}
  .db-cb-actions a:hover{text-decoration:underline;}
  .db-cb-group{display:flex;flex-direction:column;gap:3px;max-height:160px;overflow-y:auto;}
  .db-cb-label{display:flex;align-items:center;gap:6px;font-size:12px;cursor:pointer;padding:1px 0;}
  .db-cb-label input{cursor:pointer;}
  .db-cb-label.db-hide{display:none;}

  .db-range-row{display:flex;gap:6px;align-items:center;font-size:11px;}
  .db-range-input{width:0;flex:1;min-width:0;padding:4px 6px;font-size:11px;font-family:inherit;
    border:1px solid var(--border);border-radius:4px;background:var(--page-plane);color:var(--text-primary);}
  .db-text-input{width:100%;padding:5px 8px;font-size:12px;font-family:inherit;border:1px solid var(--border);
    border-radius:4px;background:var(--page-plane);color:var(--text-primary);}
  .db-select{width:100%;padding:5px 8px;font-size:12px;font-family:inherit;border:1px solid var(--border);
    border-radius:4px;background:var(--page-plane);color:var(--text-primary);}
  .db-reset-btn{width:100%;margin-top:10px;padding:7px;font-size:12px;font-family:inherit;border:1px solid var(--border);
    border-radius:4px;background:none;cursor:pointer;color:var(--text-secondary);}
  .db-reset-btn:hover{background:var(--page-plane);}
  .db-toggle-row{display:flex;align-items:center;gap:6px;font-size:12px;cursor:pointer;padding:6px 2px;}

  .db-main{overflow-y:auto;padding:16px;}
  .db-charts-row{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;}
  .db-chart-card{background:var(--surface-1);border:1px solid var(--border);border-radius:6px;padding:12px;
    resize:vertical;overflow:auto;min-height:220px;}
  .db-chart-card-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;flex-wrap:wrap;gap:6px;}
  .db-chart-card h4{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;color:var(--text-secondary);}
  .db-chart-wrap{position:relative;height:220px;}

  .db-seg{display:flex;border:1px solid var(--border);border-radius:5px;overflow:hidden;}
  .db-seg button{font-family:inherit;font-size:10px;padding:4px 8px;border:none;background:none;cursor:pointer;
    color:var(--text-secondary);border-right:1px solid var(--border);}
  .db-seg button:last-child{border-right:none;}
  .db-seg button.active{background:var(--accent);color:#fff;}
  .db-seg button:hover:not(.active){background:var(--grid-line);}

  .db-portfolio-empty{display:flex;align-items:center;justify-content:center;height:220px;text-align:center;
    color:var(--text-muted);font-size:12px;padding:0 20px;}
  .db-portfolio-body{display:none;height:260px;overflow-y:auto;}
  .db-portfolio-body.active{display:block;}
  .db-portfolio-empty.hidden{display:none;}
  .db-pf-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;}
  .db-pf-name{font-size:13px;font-weight:600;}
  .db-pf-kind{font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.04em;}
  .db-pf-close{cursor:pointer;color:var(--text-muted);font-size:14px;border:none;background:none;line-height:1;}
  .db-pf-close:hover{color:var(--text-primary);}
  .db-pf-stats{display:flex;gap:14px;margin-bottom:8px;flex-wrap:wrap;}
  .db-pf-stat .v{font-family:'DM Mono',monospace;font-size:14px;font-weight:600;}
  .db-pf-stat .l{font-size:10px;color:var(--text-muted);}
  .db-pf-list{display:flex;flex-direction:column;gap:6px;}
  .db-pf-row{border:1px solid var(--border);border-radius:5px;padding:6px 8px;font-size:11px;}
  .db-pf-row .pf-addr{font-weight:600;}
  .db-pf-row .pf-meta{color:var(--text-secondary);margin-top:2px;}
  .db-pf-note{font-size:10px;color:var(--text-muted);margin-top:8px;line-height:1.4;}

  .db-table-card{background:var(--surface-1);border:1px solid var(--border);border-radius:6px;overflow:hidden;}
  .db-table-header{padding:10px 14px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}
  .db-table-header h4{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;color:var(--text-secondary);}
  .db-export-btn{padding:4px 10px;font-size:11px;font-family:inherit;border:1px solid var(--border);border-radius:4px;background:none;cursor:pointer;color:var(--text-primary);}
  .db-table-wrap{overflow-x:auto;}
  table{width:100%;border-collapse:collapse;font-size:12px;}
  th{padding:8px 10px;text-align:left;border-bottom:2px solid var(--border);font-weight:600;font-size:11px;
    text-transform:uppercase;letter-spacing:.03em;color:var(--text-secondary);cursor:pointer;white-space:nowrap;user-select:none;}
  th:hover{color:var(--text-primary);}
  th.sort-asc::after{content:' ↑';}
  th.sort-desc::after{content:' ↓';}
  td{padding:7px 10px;border-bottom:1px solid var(--grid-line);vertical-align:top;color:var(--text-primary);}
  tr:hover td{background:var(--page-plane);}
  tr.expanded td{background:var(--page-plane);}
  .db-price{font-family:'DM Mono',monospace;white-space:nowrap;}
  .db-co-matched{color:var(--accent);font-weight:600;}
  .db-rp-badge{display:inline-flex;align-items:center;gap:3px;font-size:10px;font-weight:600;color:var(--status-warn-ink);
    background:color-mix(in srgb, var(--status-warn) 25%, transparent);border-radius:3px;padding:1px 5px;white-space:nowrap;}
  .db-pagination{padding:10px 14px;border-top:1px solid var(--border);display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text-secondary);}
  .db-pagination button{padding:4px 10px;font-size:11px;font-family:inherit;border:1px solid var(--border);border-radius:4px;background:none;cursor:pointer;color:var(--text-primary);}
  .db-pagination button:disabled{opacity:.4;cursor:default;}
  .db-row-detail{display:none;background:var(--page-plane);padding:10px;font-size:11px;}
  .db-row-detail.open{display:table-row;}
  .db-row-detail td{padding:10px;color:var(--text-secondary);}
  .db-detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px 16px;}
  .db-detail-row{display:flex;gap:6px;}
  .db-detail-row .dl{color:var(--text-muted);min-width:100px;}
  .db-detail-row .dv{font-weight:500;color:var(--text-primary);}
</style>

<div id="dashboard-tab">

  <div class="db-header">
    <div class="db-title-row">
      <h2>CORES + GETTEL Transaction Dashboard</h2>
      <span class="db-badge">Multi-Family</span>
    </div>
    <div class="db-kpis">
      <div class="db-kpi"><div class="kv" id="db-k-txns">—</div><div class="kl">Transactions</div><div class="kd" id="db-k-txns-d"></div></div>
      <div class="db-kpi"><div class="kv" id="db-k-vol">—</div><div class="kl">Total Volume</div><div class="kd" id="db-k-vol-d"></div></div>
      <div class="db-kpi"><div class="kv" id="db-k-avg">—</div><div class="kl">Avg Deal Size</div></div>
      <div class="db-kpi"><div class="kv" id="db-k-door">—</div><div class="kl">Avg $/Door</div></div>
      <div class="db-kpi"><div class="kv" id="db-k-matched">—</div><div class="kl">CORES Matches</div></div>
      <div class="db-kpi"><div class="kv" id="db-k-related">—</div><div class="kl">Related-Party</div></div>
    </div>
  </div>

  <div class="db-body">

    <div class="db-sidebar" id="db-sidebar">

      <details class="db-fgroup" open>
        <summary>Property Type</summary>
        <div class="db-fgroup-body">
          <input class="db-cb-search" data-for="db-f-type" placeholder="Search…">
          <div class="db-cb-actions"><a onclick="DB_selectAll('db-f-type',true)">All</a><a onclick="DB_selectAll('db-f-type',false)">None</a></div>
          <div class="db-cb-group" id="db-f-type"></div>
        </div>
      </details>

      <details class="db-fgroup">
        <summary>Land Use Class</summary>
        <div class="db-fgroup-body">
          <input class="db-cb-search" data-for="db-f-landuse" placeholder="Search…">
          <div class="db-cb-actions"><a onclick="DB_selectAll('db-f-landuse',true)">All</a><a onclick="DB_selectAll('db-f-landuse',false)">None</a></div>
          <div class="db-cb-group" id="db-f-landuse"></div>
        </div>
      </details>

      <details class="db-fgroup">
        <summary>City</summary>
        <div class="db-fgroup-body">
          <select class="db-select" id="db-f-city"><option value="">All Cities</option></select>
        </div>
      </details>

      <details class="db-fgroup">
        <summary>Subdivision</summary>
        <div class="db-fgroup-body">
          <select class="db-select" id="db-f-subdiv"><option value="">All Subdivisions</option></select>
        </div>
      </details>

      <details class="db-fgroup" open>
        <summary>Year Sold</summary>
        <div class="db-fgroup-body">
          <div class="db-range-row">
            <input class="db-range-input" id="db-f-year-from" type="number" placeholder="From">
            <span>–</span>
            <input class="db-range-input" id="db-f-year-to" type="number" placeholder="To">
          </div>
        </div>
      </details>

      <details class="db-fgroup">
        <summary>Year Built</summary>
        <div class="db-fgroup-body">
          <div class="db-range-row">
            <input class="db-range-input" id="db-f-yb-from" type="number" placeholder="From">
            <span>–</span>
            <input class="db-range-input" id="db-f-yb-to" type="number" placeholder="To">
          </div>
        </div>
      </details>

      <details class="db-fgroup" open>
        <summary>Sale Price ($)</summary>
        <div class="db-fgroup-body">
          <div class="db-range-row">
            <input class="db-range-input" id="db-f-price-from" type="number" placeholder="Min">
            <span>–</span>
            <input class="db-range-input" id="db-f-price-to" type="number" placeholder="Max">
          </div>
        </div>
      </details>

      <details class="db-fgroup">
        <summary>$ / Door</summary>
        <div class="db-fgroup-body">
          <div class="db-range-row">
            <input class="db-range-input" id="db-f-door-from" type="number" placeholder="Min">
            <span>–</span>
            <input class="db-range-input" id="db-f-door-to" type="number" placeholder="Max">
          </div>
        </div>
      </details>

      <details class="db-fgroup">
        <summary>$ / Acre</summary>
        <div class="db-fgroup-body">
          <div class="db-range-row">
            <input class="db-range-input" id="db-f-acre-from" type="number" placeholder="Min">
            <span>–</span>
            <input class="db-range-input" id="db-f-acre-to" type="number" placeholder="Max">
          </div>
        </div>
      </details>

      <details class="db-fgroup">
        <summary>Cap Rate (%)</summary>
        <div class="db-fgroup-body">
          <div class="db-range-row">
            <input class="db-range-input" id="db-f-cap-from" type="number" step="0.1" placeholder="Min">
            <span>–</span>
            <input class="db-range-input" id="db-f-cap-to" type="number" step="0.1" placeholder="Max">
          </div>
        </div>
      </details>

      <details class="db-fgroup">
        <summary>Site Area</summary>
        <div class="db-fgroup-body">
          <div class="db-range-row">
            <input class="db-range-input" id="db-f-site-from" type="number" placeholder="Min">
            <span>–</span>
            <input class="db-range-input" id="db-f-site-to" type="number" placeholder="Max">
          </div>
        </div>
      </details>

      <details class="db-fgroup">
        <summary>Total Units</summary>
        <div class="db-fgroup-body">
          <div class="db-range-row">
            <input class="db-range-input" id="db-f-units-from" type="number" placeholder="Min">
            <span>–</span>
            <input class="db-range-input" id="db-f-units-to" type="number" placeholder="Max">
          </div>
        </div>
      </details>

      <details class="db-fgroup" open>
        <summary>Search</summary>
        <div class="db-fgroup-body">
          <input class="db-text-input" id="db-f-company" placeholder="Vendor or purchaser…" style="margin-bottom:6px;">
          <input class="db-text-input" id="db-f-person" placeholder="Director / shareholder…">
        </div>
      </details>

      <label class="db-toggle-row">
        <input type="checkbox" id="db-f-cores-only"> CORES matches only
      </label>
      <label class="db-toggle-row">
        <input type="checkbox" id="db-f-related-only"> Related-party only
      </label>

      <button class="db-reset-btn" onclick="DB_resetAll()">Reset All Filters</button>
    </div>

    <div class="db-main">
      <div class="db-charts-row">
        <div class="db-chart-card">
          <div class="db-chart-card-head">
            <h4>Volume by Year</h4>
            <div class="db-seg" id="db-year-mode">
              <button class="active" data-mode="volume" onclick="DB_setYearMode('volume')">$ Volume</button>
              <button data-mode="door" onclick="DB_setYearMode('door')">$/Door</button>
            </div>
          </div>
          <div class="db-chart-wrap"><canvas id="db-chart-year"></canvas></div>
        </div>
        <div class="db-chart-card" id="db-portfolio-card">
          <div class="db-chart-card-head">
            <h4>Portfolio</h4>
          </div>
          <div class="db-portfolio-empty" id="db-pf-empty">Click a bar in Top 20 Companies or Top 20 People to view current holdings.</div>
          <div class="db-portfolio-body" id="db-pf-body">
            <div class="db-pf-head">
              <div>
                <div class="db-pf-name" id="db-pf-name"></div>
                <div class="db-pf-kind" id="db-pf-kind"></div>
              </div>
              <button class="db-pf-close" onclick="DB_closePortfolio()">✕</button>
            </div>
            <div class="db-pf-stats">
              <div class="db-pf-stat"><div class="v" id="db-pf-held">—</div><div class="l">Currently Held</div></div>
              <div class="db-pf-stat"><div class="v" id="db-pf-vol">—</div><div class="l">Purchase Volume</div></div>
              <div class="db-pf-stat"><div class="v" id="db-pf-hold">—</div><div class="l">Avg Hold (resold)</div></div>
            </div>
            <div class="db-pf-list" id="db-pf-list"></div>
            <div class="db-pf-note">Ownership inferred from purchase records with no later transaction at the same legal description. A condo conversion / de-condo changes the legal description and will break this chain.</div>
          </div>
        </div>
      </div>
      <div class="db-charts-row">
        <div class="db-chart-card">
          <div class="db-chart-card-head">
            <h4>Top 20 Companies</h4>
            <div class="db-seg" id="db-cos-mode">
              <button class="active" data-mode="count" onclick="DB_setRankMode('cos','count')">Deals</button>
              <button data-mode="volume" onclick="DB_setRankMode('cos','volume')">$ Volume</button>
              <button data-mode="units" onclick="DB_setRankMode('cos','units')">Units</button>
            </div>
          </div>
          <div class="db-chart-wrap" style="height:260px"><canvas id="db-chart-cos"></canvas></div>
        </div>
        <div class="db-chart-card">
          <div class="db-chart-card-head">
            <h4>Top 20 People</h4>
            <div class="db-seg" id="db-ppl-mode">
              <button class="active" data-mode="count" onclick="DB_setRankMode('ppl','count')">Deals</button>
              <button data-mode="volume" onclick="DB_setRankMode('ppl','volume')">$ Volume</button>
              <button data-mode="units" onclick="DB_setRankMode('ppl','units')">Units</button>
            </div>
          </div>
          <div class="db-chart-wrap" style="height:260px"><canvas id="db-chart-people"></canvas></div>
        </div>
      </div>

      <div class="db-table-card">
        <div class="db-table-header">
          <h4 id="db-table-title">Transactions</h4>
          <button class="db-export-btn" onclick="DB_exportCSV()">Export CSV</button>
        </div>
        <div class="db-table-wrap">
          <table id="db-table">
            <thead><tr>
              <th style="width:36px">#</th>
              <th data-col="sale_date" onclick="DB_sort('sale_date')">Date</th>
              <th data-col="city" onclick="DB_sort('city')">City</th>
              <th data-col="property_type" onclick="DB_sort('property_type')">Type</th>
              <th>Description</th>
              <th>Vendor</th>
              <th>Purchaser</th>
              <th data-col="sale_price" onclick="DB_sort('sale_price')">Price</th>
              <th data-col="unit_price" onclick="DB_sort('unit_price')">$/Unit</th>
              <th data-col="cap_rate" onclick="DB_sort('cap_rate')">Cap Rate</th>
              <th style="width:30px"></th>
            </tr></thead>
            <tbody id="db-tbody"></tbody>
          </table>
        </div>
        <div class="db-pagination">
          <button id="db-pg-prev" onclick="DB_page(-1)">← Prev</button>
          <span id="db-pg-info"></span>
          <button id="db-pg-next" onclick="DB_page(1)">Next →</button>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
(function(){
const DB_DATA = """ + dashboard_data + r""";

const TXNS = DB_DATA.transactions;
const FOPTS = DB_DATA.filter_options;

let DB_filtered = [...TXNS];
let DB_page_num = 1;
const DB_PAGE_SIZE = 50;
let DB_sort_col = 'sale_date';
let DB_sort_dir = 'desc';

let DB_charts = {};
let DB_year_mode = 'volume';
let DB_rank_mode = { cos: 'count', ppl: 'count' };

function fmtPrice(v){
  if(v==null||v===''||v===undefined) return '—';
  v = parseFloat(v);
  if(isNaN(v)) return '—';
  if(Math.abs(v)>=1e9) return '$'+(v/1e9).toFixed(2)+'B';
  if(Math.abs(v)>=1e6) return '$'+(v/1e6).toFixed(1)+'M';
  if(Math.abs(v)>=1e3) return '$'+(v/1e3).toFixed(0)+'K';
  return '$'+v.toLocaleString();
}
function fmtArea(v,u){return v?(parseFloat(v)||0).toLocaleString()+' '+(u||''):'—';}
function fmtPct(v){return (v==null||isNaN(v))?'—':(parseFloat(v).toFixed(2)+'%');}

// ─── LEGAL-DESCRIPTION RESALE INDEX (for portfolio matching) ──────────────────
function normalizeLegal(s){
  return (s||'').toUpperCase().replace(/[^A-Z0-9]/g,'');
}
const LEGAL_INDEX = (function(){
  const idx = {};
  TXNS.forEach(t=>{
    const key = normalizeLegal(t.legal_description);
    if(!key) return;
    (idx[key] = idx[key]||[]).push(t);
  });
  Object.values(idx).forEach(arr=>arr.sort((a,b)=>(a.sale_date||'').localeCompare(b.sale_date||'')));
  return idx;
})();

function computePortfolio(name, kind){
  const field = kind==='person' ? 'purchaser_person' : 'purchaser_entity';
  const purchases = TXNS.filter(t=>t[field]===name);
  const held = [], resold = [];
  purchases.forEach(t=>{
    const key = normalizeLegal(t.legal_description);
    const chain = key ? (LEGAL_INDEX[key]||[t]) : [t];
    const later = chain.find(c=>c.txn_id!==t.txn_id && (c.sale_date||'') > (t.sale_date||''));
    if(later){ resold.push({purchase:t, resale:later}); }
    else { held.push(t); }
  });
  return {held, resold};
}

// ─── INIT FILTERS ────────────────────────────────────────────────────────────
function buildCBGroup(containerId, options, onChange){
  const c = document.getElementById(containerId);
  options.forEach(opt=>{
    const lbl = document.createElement('label');
    lbl.className='db-cb-label';
    lbl.innerHTML=`<input type="checkbox" value="${opt}" checked> ${opt}`;
    lbl.querySelector('input').addEventListener('change', onChange);
    c.appendChild(lbl);
  });
}

buildCBGroup('db-f-type',    FOPTS.property_types,   DB_applyFilters);
buildCBGroup('db-f-landuse', FOPTS.land_use_classes,  DB_applyFilters);

document.querySelectorAll('.db-cb-search').forEach(inp=>{
  inp.addEventListener('input', ()=>{
    const target = document.getElementById(inp.dataset.for);
    const q = inp.value.toLowerCase();
    target.querySelectorAll('.db-cb-label').forEach(lbl=>{
      const txt = lbl.textContent.toLowerCase();
      lbl.classList.toggle('db-hide', q && !txt.includes(q));
    });
  });
});

window.DB_selectAll = function(containerId, checked){
  document.querySelectorAll(`#${containerId} input[type=checkbox]`).forEach(el=>{
    if(!el.closest('.db-cb-label').classList.contains('db-hide')) el.checked = checked;
  });
  DB_applyFilters();
};

const cityEl = document.getElementById('db-f-city');
FOPTS.cities.sort().forEach(c=>{const o=document.createElement('option');o.value=c;o.textContent=c;cityEl.appendChild(o);});
cityEl.addEventListener('change', DB_applyFilters);

const subdivEl = document.getElementById('db-f-subdiv');
FOPTS.subdivisions.sort().forEach(s=>{const o=document.createElement('option');o.value=s;o.textContent=s;subdivEl.appendChild(o);});
subdivEl.addEventListener('change', DB_applyFilters);

const RANGE_IDS = ['db-f-year-from','db-f-year-to','db-f-yb-from','db-f-yb-to',
  'db-f-price-from','db-f-price-to','db-f-door-from','db-f-door-to',
  'db-f-acre-from','db-f-acre-to','db-f-cap-from','db-f-cap-to',
  'db-f-site-from','db-f-site-to','db-f-units-from','db-f-units-to',
  'db-f-company','db-f-person'];
RANGE_IDS.forEach(id=>{
  document.getElementById(id).addEventListener('input', DB_applyFilters);
});
document.getElementById('db-f-cores-only').addEventListener('change', DB_applyFilters);
document.getElementById('db-f-related-only').addEventListener('change', DB_applyFilters);

const years = FOPTS.years.filter(y=>y);
if(years.length){
  document.getElementById('db-f-year-from').placeholder = Math.min(...years);
  document.getElementById('db-f-year-to').placeholder   = Math.max(...years);
}

// ─── FILTER LOGIC ────────────────────────────────────────────────────────────
function getChecked(containerId){
  return [...document.querySelectorAll(`#${containerId} input[type=checkbox]:checked`)].map(el=>el.value);
}
function rangeVal(id){ const v = document.getElementById(id).value; return v===''? null : parseFloat(v); }

function DB_applyFilters(){
  const types    = getChecked('db-f-type');
  const landUse  = getChecked('db-f-landuse');
  const city     = document.getElementById('db-f-city').value;
  const subdiv   = document.getElementById('db-f-subdiv').value;
  const yFrom    = rangeVal('db-f-year-from'), yTo = rangeVal('db-f-year-to');
  const ybFrom   = rangeVal('db-f-yb-from'),   ybTo = rangeVal('db-f-yb-to');
  const pFrom    = rangeVal('db-f-price-from'),pTo = rangeVal('db-f-price-to');
  const doorFrom = rangeVal('db-f-door-from'), doorTo = rangeVal('db-f-door-to');
  const acreFrom = rangeVal('db-f-acre-from'), acreTo = rangeVal('db-f-acre-to');
  const capFrom  = rangeVal('db-f-cap-from'),  capTo = rangeVal('db-f-cap-to');
  const siteFrom = rangeVal('db-f-site-from'), siteTo = rangeVal('db-f-site-to');
  const unitsFrom= rangeVal('db-f-units-from'),unitsTo = rangeVal('db-f-units-to');
  const coQ      = document.getElementById('db-f-company').value.toLowerCase();
  const peQ      = document.getElementById('db-f-person').value.toLowerCase();
  const coresOnly= document.getElementById('db-f-cores-only').checked;
  const relOnly  = document.getElementById('db-f-related-only').checked;

  function inRange(v, from, to){
    if(v==null) return from==null && to==null;
    if(from!=null && v<from) return false;
    if(to!=null && v>to) return false;
    return true;
  }

  DB_filtered = TXNS.filter(t=>{
    if(!types.includes(t.property_type))   return false;
    if(landUse.length && t.land_use && !landUse.includes(t.land_use)) return false;
    if(city   && t.city !== city)           return false;
    if(subdiv && t.subdivision !== subdiv)  return false;
    const yr = parseInt(t.sale_year)||0;
    if(yFrom!=null && yr < yFrom) return false;
    if(yTo!=null && yr > yTo) return false;
    if((ybFrom!=null||ybTo!=null) && !inRange(t.year_built, ybFrom, ybTo)) return false;
    const pr = parseFloat(t.sale_price)||0;
    if(pFrom!=null && pr < pFrom) return false;
    if(pTo!=null && pr > pTo) return false;
    if((doorFrom!=null||doorTo!=null) && !inRange(t.price_per_door, doorFrom, doorTo)) return false;
    if((acreFrom!=null||acreTo!=null) && !inRange(t.price_per_acre, acreFrom, acreTo)) return false;
    if((capFrom!=null||capTo!=null) && !inRange(t.cap_rate, capFrom, capTo)) return false;
    if((siteFrom!=null||siteTo!=null) && !inRange(t.site_area, siteFrom, siteTo)) return false;
    if((unitsFrom!=null||unitsTo!=null) && !inRange(t.total_units, unitsFrom, unitsTo)) return false;
    if(coQ && !(t.vendor_entity||'').toLowerCase().includes(coQ) &&
             !(t.purchaser_entity||'').toLowerCase().includes(coQ)) return false;
    if(peQ && !(t.vendor_person||'').toLowerCase().includes(peQ) &&
             !(t.purchaser_person||'').toLowerCase().includes(peQ)) return false;
    if(coresOnly && !t.vendor_can && !t.purchaser_can) return false;
    if(relOnly && !t.related_party) return false;
    return true;
  });

  DB_page_num = 1;
  updateKPIs();
  updateCharts();
  renderTable();
}
window.DB_applyFilters = DB_applyFilters;

function updateKPIs(){
  const prices  = DB_filtered.map(t=>parseFloat(t.sale_price)).filter(v=>!isNaN(v)&&v>0);
  const vol     = prices.reduce((s,v)=>s+v,0);
  const avg     = prices.length ? vol/prices.length : 0;
  const doors   = DB_filtered.map(t=>parseFloat(t.price_per_door)).filter(v=>!isNaN(v)&&v>0);
  const avgDoor = doors.length ? doors.reduce((s,v)=>s+v,0)/doors.length : 0;
  const matched = DB_filtered.filter(t=>t.vendor_can||t.purchaser_can).length;
  const related = DB_filtered.filter(t=>t.related_party).length;

  document.getElementById('db-k-txns').textContent    = DB_filtered.length.toLocaleString();
  document.getElementById('db-k-vol').textContent     = fmtPrice(vol);
  document.getElementById('db-k-avg').textContent     = fmtPrice(avg);
  document.getElementById('db-k-door').textContent    = avgDoor ? fmtPrice(avgDoor) : '—';
  document.getElementById('db-k-matched').textContent = matched.toLocaleString();
  document.getElementById('db-k-related').textContent = related.toLocaleString();
  document.getElementById('db-table-title').textContent = `Transactions (${DB_filtered.length.toLocaleString()})`;

  if(DB_filtered.length < TXNS.length){
    document.getElementById('db-k-txns-d').textContent = `${((DB_filtered.length/TXNS.length)*100).toFixed(1)}% of all`;
    const allPrices = TXNS.map(t=>parseFloat(t.sale_price)).filter(v=>!isNaN(v)&&v>0);
    const allVol = allPrices.reduce((s,v)=>s+v,0);
    document.getElementById('db-k-vol-d').textContent = allVol ? `${((vol/allVol)*100).toFixed(1)}% of all` : '';
  } else {
    document.getElementById('db-k-txns-d').textContent = '';
    document.getElementById('db-k-vol-d').textContent = '';
  }
}

// ─── CHARTS ──────────────────────────────────────────────────────────────────
const DB_CS = getComputedStyle(document.getElementById('dashboard-tab'));
const ACCENT      = DB_CS.getPropertyValue('--accent').trim() || '#2a78d6';
const ACCENT_2     = DB_CS.getPropertyValue('--accent-2').trim() || '#1baf7a';
const GRID_LINE    = DB_CS.getPropertyValue('--grid-line').trim() || '#e1e0d9';
const TEXT_MUTED   = DB_CS.getPropertyValue('--text-muted').trim() || '#898781';
const MUTED_GREY   = '#aaa';

function updateCharts(){
  updateYearChart();
  updateCosChart();
  updatePeopleChart();
}

window.DB_setYearMode = function(mode){
  DB_year_mode = mode;
  document.querySelectorAll('#db-year-mode button').forEach(b=>b.classList.toggle('active', b.dataset.mode===mode));
  updateYearChart();
};

function updateYearChart(){
  let years, data, label, fmt;
  if(DB_year_mode==='volume'){
    const byYear = {};
    DB_filtered.forEach(t=>{
      const y = t.sale_year||'Unknown';
      byYear[y] = (byYear[y]||0) + (parseFloat(t.sale_price)||0);
    });
    years = Object.keys(byYear).sort();
    data  = years.map(y=>byYear[y]);
    label = 'Total $ Volume';
    fmt   = fmtPrice;
  } else {
    const byYear = {};
    DB_filtered.forEach(t=>{
      const dp = parseFloat(t.price_per_door);
      if(isNaN(dp) || dp<=0) return;
      const y = t.sale_year||'Unknown';
      (byYear[y] = byYear[y]||[]).push(dp);
    });
    years = Object.keys(byYear).sort();
    data  = years.map(y=>{ const arr=byYear[y]; return arr.reduce((s,v)=>s+v,0)/arr.length; });
    label = 'Avg $/Door';
    fmt   = fmtPrice;
  }

  const dataset = {label, data, backgroundColor: ACCENT, borderRadius:3};

  if(DB_charts.year){
    DB_charts.year.data.labels = years;
    DB_charts.year.data.datasets = [dataset];
    DB_charts.year.options.plugins.tooltip.callbacks.label = ctx=>`${label}: ${fmt(ctx.raw)}`;
    DB_charts.year.options.scales.y.ticks.callback = v=>fmt(v);
    DB_charts.year.update();
  } else {
    DB_charts.year = new Chart(document.getElementById('db-chart-year'),{
      type:'bar',
      data:{labels:years, datasets:[dataset]},
      options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx=>`${label}: ${fmt(ctx.raw)}`}}},
        scales:{x:{grid:{display:false},ticks:{color:TEXT_MUTED}},y:{ticks:{callback:v=>fmt(v),color:TEXT_MUTED},grid:{color:GRID_LINE}}},
      }
    });
  }
}

function aggregateLeaderboard(field, mode){
  const map = {};
  DB_filtered.forEach(t=>{
    [['vendor_'+field,'vendor_can','vendor_type'],['purchaser_'+field,'purchaser_can','purchaser_type']].forEach(([nameField, canField])=>{
      const name = t[nameField];
      if(!name) return;
      if(!map[name]) map[name] = {count:0, volume:0, units:0, matched:false};
      map[name].count += 1;
      map[name].volume += parseFloat(t.sale_price)||0;
      map[name].units  += parseFloat(t.total_units)||0;
      if(t[canField]) map[name].matched = true;
    });
  });
  const sorted = Object.entries(map).sort((a,b)=>b[1][mode]-a[1][mode]).slice(0,20);
  return sorted;
}

window.DB_setRankMode = function(chart, mode){
  DB_rank_mode[chart] = mode;
  document.querySelectorAll(`#db-${chart}-mode button`).forEach(b=>b.classList.toggle('active', b.dataset.mode===mode));
  if(chart==='cos') updateCosChart(); else updatePeopleChart();
};

function renderLeaderboard(chartKey, canvasId, field, mode, kind){
  const sorted = aggregateLeaderboard(field, mode);
  const labels = sorted.map(e=>e[0].length>30?e[0].slice(0,28)+'…':e[0]);
  const fullNames = sorted.map(e=>e[0]);
  const data   = sorted.map(e=>e[1][mode]);
  const colors = sorted.map(e=>e[1].matched?ACCENT:MUTED_GREY);
  const fmtVal = mode==='volume' ? fmtPrice : (v=>v.toLocaleString());

  const existing = DB_charts[chartKey];
  if(existing){
    existing.data.labels = labels;
    existing.data.datasets[0].data = data;
    existing.data.datasets[0].backgroundColor = colors;
    existing.options.plugins.tooltip.callbacks.label = ctx=>fmtVal(ctx.raw);
    existing.update();
  } else {
    DB_charts[chartKey] = new Chart(document.getElementById(canvasId),{
      type:'bar',
      data:{labels,datasets:[{data,backgroundColor:colors,borderWidth:0,borderRadius:2}]},
      options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx=>fmtVal(ctx.raw)}}},
        scales:{x:{ticks:{callback:v=>mode==='volume'?fmtPrice(v):v,color:TEXT_MUTED},grid:{color:GRID_LINE}},y:{ticks:{font:{size:10},color:TEXT_MUTED},grid:{display:false}}},
        onClick:(evt, els)=>{
          if(!els.length) return;
          const idx = els[0].index;
          DB_showPortfolio(fullNames[idx], kind);
        },
        onHover:(evt, els)=>{ evt.native.target.style.cursor = els.length ? 'pointer' : 'default'; },
      }
    });
  }
}

function updateCosChart(){ renderLeaderboard('cos','db-chart-cos','entity', DB_rank_mode.cos, 'company'); }
function updatePeopleChart(){ renderLeaderboard('ppl','db-chart-people','person', DB_rank_mode.ppl, 'person'); }

// ─── PORTFOLIO PANEL ─────────────────────────────────────────────────────────
window.DB_showPortfolio = function(name, kind){
  const {held, resold} = computePortfolio(name, kind);
  document.getElementById('db-pf-empty').classList.add('hidden');
  document.getElementById('db-pf-body').classList.add('active');
  document.getElementById('db-pf-name').textContent = name;
  document.getElementById('db-pf-kind').textContent = kind==='person' ? 'Person' : 'Company';

  const totalVol = held.reduce((s,t)=>s+(parseFloat(t.sale_price)||0),0) +
                   resold.reduce((s,r)=>s+(parseFloat(r.purchase.sale_price)||0),0);
  document.getElementById('db-pf-held').textContent = held.length.toLocaleString();
  document.getElementById('db-pf-vol').textContent   = fmtPrice(totalVol);

  if(resold.length){
    const days = resold.map(r=>{
      const d1 = new Date(r.purchase.sale_date), d2 = new Date(r.resale.sale_date);
      return (d2-d1)/(1000*60*60*24);
    }).filter(d=>!isNaN(d)&&d>=0);
    const avgDays = days.length ? days.reduce((s,v)=>s+v,0)/days.length : null;
    document.getElementById('db-pf-hold').textContent = avgDays!=null ? `${(avgDays/365).toFixed(1)} yr` : '—';
  } else {
    document.getElementById('db-pf-hold').textContent = '—';
  }

  const list = document.getElementById('db-pf-list');
  list.innerHTML = '';
  if(!held.length){
    const div = document.createElement('div');
    div.className = 'db-pf-row';
    div.textContent = 'No properties currently held (all tracked purchases show a later sale at the same legal description, or none matched).';
    list.appendChild(div);
  }
  held.sort((a,b)=>(b.sale_date||'').localeCompare(a.sale_date||'')).forEach(t=>{
    const div = document.createElement('div');
    div.className = 'db-pf-row';
    const priceNote = t.price_per_door ? fmtPrice(t.price_per_door)+'/door' : (t.price_per_acre ? fmtPrice(t.price_per_acre)+'/acre' : fmtPrice(t.sale_price));
    div.innerHTML = `<div class="pf-addr">${t.address||t.legal_description||'—'}</div>
      <div class="pf-meta">${t.city||'—'} · ${t.land_use||'—'} · purchased ${t.sale_date||'—'} · ${fmtPrice(t.sale_price)} (${priceNote})</div>`;
    list.appendChild(div);
  });
};

window.DB_closePortfolio = function(){
  document.getElementById('db-pf-empty').classList.remove('hidden');
  document.getElementById('db-pf-body').classList.remove('active');
};

// ─── TABLE ───────────────────────────────────────────────────────────────────
function renderTable(){
  const sortMul = DB_sort_dir==='asc'?1:-1;
  const sorted  = [...DB_filtered].sort((a,b)=>{
    const av=a[DB_sort_col]||'', bv=b[DB_sort_col]||'';
    if(typeof av==='number'||!isNaN(parseFloat(av))){
      return ((parseFloat(av)||0)-(parseFloat(bv)||0))*sortMul;
    }
    return av<bv?-sortMul:av>bv?sortMul:0;
  });

  document.querySelectorAll('#db-table th[data-col]').forEach(th=>{
    th.classList.remove('sort-asc','sort-desc');
    if(th.dataset.col===DB_sort_col) th.classList.add(DB_sort_dir==='asc'?'sort-asc':'sort-desc');
  });

  const start = (DB_page_num-1)*DB_PAGE_SIZE;
  const page  = sorted.slice(start, start+DB_PAGE_SIZE);
  const total = sorted.length;
  const pages = Math.ceil(total/DB_PAGE_SIZE);

  const tbody = document.getElementById('db-tbody');
  tbody.innerHTML='';
  page.forEach((t,i)=>{
    const n = start+i+1;
    const vMatch = t.vendor_can?'db-co-matched':'';
    const pMatch = t.purchaser_can?'db-co-matched':'';
    const rpBadge = t.related_party ? '<span class="db-rp-badge">⚠ Related</span>' : '';
    const tr = document.createElement('tr');
    tr.style.cursor='pointer';
    tr.innerHTML=`
      <td>${n}</td>
      <td>${t.sale_date||'—'}</td>
      <td>${t.city||'—'}</td>
      <td>${t.property_type||'—'}</td>
      <td title="${t.description||''}">${(t.description||'').slice(0,20)}</td>
      <td class="${vMatch}" title="${t.vendor_entity||''}">${(t.vendor_entity||'—').slice(0,20)}</td>
      <td class="${pMatch}" title="${t.purchaser_entity||''}">${(t.purchaser_entity||'—').slice(0,20)}</td>
      <td class="db-price">${fmtPrice(t.sale_price)}</td>
      <td class="db-price">${t.unit_price?fmtPrice(t.unit_price)+(t.unit_measure?'/'+t.unit_measure:''):'—'}</td>
      <td class="db-price">${fmtPct(t.cap_rate)}</td>
      <td>${rpBadge}</td>`;
    const detailId = `dbr-${t.txn_id}`;
    tr.onclick=()=>DB_toggleRow(detailId, t);
    tbody.appendChild(tr);

    const det = document.createElement('tr');
    det.className='db-row-detail';
    det.id=detailId;
    det.innerHTML=`<td colspan="11"><div class="db-detail-grid">
      <div class="db-detail-row"><span class="dl">Address</span><span class="dv">${t.address||'—'}</span></div>
      <div class="db-detail-row"><span class="dl">Legal Desc</span><span class="dv">${t.legal_description||'—'}</span></div>
      <div class="db-detail-row"><span class="dl">Subdivision</span><span class="dv">${t.subdivision||'—'}</span></div>
      <div class="db-detail-row"><span class="dl">Land Use</span><span class="dv">${t.land_use||'—'}</span></div>
      <div class="db-detail-row"><span class="dl">Ownership</span><span class="dv">${t.ownership_type||'—'}</span></div>
      <div class="db-detail-row"><span class="dl">Year Built</span><span class="dv">${t.year_built||'—'}</span></div>
      <div class="db-detail-row"><span class="dl">Site Area</span><span class="dv">${fmtArea(t.site_area,t.site_units)}</span></div>
      <div class="db-detail-row"><span class="dl">Bldg Area</span><span class="dv">${fmtArea(t.bldg_area,t.bldg_units)}</span></div>
      <div class="db-detail-row"><span class="dl">Total Units</span><span class="dv">${t.total_units||'—'}</span></div>
      <div class="db-detail-row"><span class="dl">Cap Rate</span><span class="dv">${fmtPct(t.cap_rate)}</span></div>
      <div class="db-detail-row"><span class="dl">Vendor</span><span class="dv">${t.vendor_entity||'—'}${t.vendor_person?' · '+t.vendor_role+': '+t.vendor_person:''}${t.vendor_can?' [CORES '+t.vendor_can+']':''}</span></div>
      <div class="db-detail-row"><span class="dl">Purchaser</span><span class="dv">${t.purchaser_entity||'—'}${t.purchaser_person?' · '+t.purchaser_role+': '+t.purchaser_person:''}${t.purchaser_can?' [CORES '+t.purchaser_can+']':''}</span></div>
      ${t.related_party ? '<div class="db-detail-row"><span class="dl">Flag</span><span class="dv">⚠ Related-party transaction — vendor and purchaser share a named person or a CORES-matched director/shareholder.</span></div>' : ''}
    </div></td>`;
    tbody.appendChild(det);
  });

  document.getElementById('db-pg-info').textContent = `Page ${DB_page_num} of ${pages} (${total.toLocaleString()} rows)`;
  document.getElementById('db-pg-prev').disabled = DB_page_num<=1;
  document.getElementById('db-pg-next').disabled = DB_page_num>=pages;
}

window.DB_toggleRow = function(id, t){
  const el = document.getElementById(id);
  if(el) el.classList.toggle('open');
};

window.DB_sort = function(col){
  if(DB_sort_col===col) DB_sort_dir=DB_sort_dir==='asc'?'desc':'asc';
  else{DB_sort_col=col;DB_sort_dir='desc';}
  DB_page_num=1;
  renderTable();
};

window.DB_page = function(dir){
  const pages = Math.ceil(DB_filtered.length/DB_PAGE_SIZE);
  DB_page_num = Math.max(1, Math.min(pages, DB_page_num+dir));
  renderTable();
};

window.DB_resetAll = function(){
  document.querySelectorAll('#db-f-type input, #db-f-landuse input').forEach(el=>el.checked=true);
  document.querySelectorAll('.db-cb-search').forEach(el=>el.value='');
  document.querySelectorAll('.db-cb-label').forEach(el=>el.classList.remove('db-hide'));
  ['db-f-city','db-f-subdiv'].forEach(id=>document.getElementById(id).value='');
  RANGE_IDS.forEach(id=>document.getElementById(id).value='');
  document.getElementById('db-f-cores-only').checked=false;
  document.getElementById('db-f-related-only').checked=false;
  DB_applyFilters();
};

window.DB_exportCSV = function(){
  const cols = ['txn_id','sale_date','city','property_type','ownership_type','land_use',
    'description','address','legal_description','vendor_entity','vendor_person','vendor_role','vendor_can',
    'purchaser_entity','purchaser_person','purchaser_role','purchaser_can',
    'sale_price','unit_price','unit_measure','price_per_door','price_per_acre','cap_rate','total_units',
    'bldg_area','site_area','year_built','subdivision','related_party'];
  const csv  = [cols.join(',')].concat(DB_filtered.map(t=>
    cols.map(c=>JSON.stringify(t[c]||'')).join(',')
  )).join('\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  a.download = 'cores_gettel_filtered.csv';
  a.click();
};

// ─── INIT ────────────────────────────────────────────────────────────────────
DB_applyFilters();

})();
</script>
"""

with open("dashboard_section.html","w",encoding="utf-8") as f:
    f.write(html)

print("dashboard_section.html written.")
print(f"  File size: {len(html)/1024:.0f} KB (excluding embedded data)")
