# @title 3 — TRANSACTION DASHBOARD (HTML)
# Input: dashboard_data.json
# Output: dashboard_section.html

import json

with open("dashboard_data.json","r",encoding="utf-8") as f:
    dashboard_data = f.read()

html = r"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
  #dashboard-tab *{box-sizing:border-box;margin:0;padding:0;}
  #dashboard-tab{font-family:'DM Sans',sans-serif;background:#f8f8f6;color:#1a1a1a;min-height:100vh;}

  .db-header{background:#fff;border-bottom:1px solid #e0e0da;padding:12px 20px;}
  .db-header h2{font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;color:#6b6b6b;margin-bottom:10px;}
  .db-kpis{display:flex;gap:16px;flex-wrap:wrap;}
  .db-kpi{background:#f8f8f6;border:1px solid #e0e0da;border-radius:6px;padding:8px 14px;min-width:120px;}
  .db-kpi .kv{font-size:20px;font-weight:600;font-family:'DM Mono',monospace;}
  .db-kpi .kl{font-size:11px;color:#6b6b6b;margin-top:2px;}

  .db-body{display:grid;grid-template-columns:220px 1fr;height:calc(100vh - 90px);}

  .db-sidebar{background:#fff;border-right:1px solid #e0e0da;overflow-y:auto;padding:14px 12px;}
  .db-sidebar h3{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:#6b6b6b;margin:12px 0 6px;}
  .db-sidebar h3:first-child{margin-top:0;}
  .db-cb-group{display:flex;flex-direction:column;gap:4px;}
  .db-cb-label{display:flex;align-items:center;gap:6px;font-size:12px;cursor:pointer;}
  .db-cb-label input{cursor:pointer;}
  .db-range-row{display:flex;gap:6px;align-items:center;font-size:11px;margin-bottom:4px;}
  .db-range-input{width:80px;padding:4px 6px;font-size:11px;font-family:inherit;border:1px solid #e0e0da;border-radius:4px;background:#f8f8f6;}
  .db-text-input{width:100%;padding:5px 8px;font-size:12px;font-family:inherit;border:1px solid #e0e0da;border-radius:4px;background:#f8f8f6;margin-bottom:4px;}
  .db-select{width:100%;padding:5px 8px;font-size:12px;font-family:inherit;border:1px solid #e0e0da;border-radius:4px;background:#f8f8f6;margin-bottom:4px;}
  .db-reset-btn{width:100%;margin-top:10px;padding:7px;font-size:12px;font-family:inherit;border:1px solid #e0e0da;border-radius:4px;background:none;cursor:pointer;color:#6b6b6b;}
  .db-reset-btn:hover{background:#f4f4f2;}
  .db-cores-row{display:flex;align-items:center;gap:6px;font-size:12px;cursor:pointer;margin-bottom:4px;}

  .db-main{overflow-y:auto;padding:16px;}
  .db-charts-row{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;}
  .db-chart-card{background:#fff;border:1px solid #e0e0da;border-radius:6px;padding:12px;resize:vertical;overflow:auto;min-height:200px;}
  .db-chart-card h4{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;color:#6b6b6b;margin-bottom:10px;}
  .db-chart-wrap{position:relative;height:220px;}

  .db-table-card{background:#fff;border:1px solid #e0e0da;border-radius:6px;overflow:hidden;}
  .db-table-header{padding:10px 14px;border-bottom:1px solid #e0e0da;display:flex;align-items:center;justify-content:space-between;}
  .db-table-header h4{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;color:#6b6b6b;}
  .db-export-btn{padding:4px 10px;font-size:11px;font-family:inherit;border:1px solid #e0e0da;border-radius:4px;background:none;cursor:pointer;}
  .db-table-wrap{overflow-x:auto;}
  table{width:100%;border-collapse:collapse;font-size:12px;}
  th{padding:8px 10px;text-align:left;border-bottom:2px solid #e0e0da;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.03em;color:#6b6b6b;cursor:pointer;white-space:nowrap;user-select:none;}
  th:hover{color:#111;}
  th.sort-asc::after{content:' ↑';}
  th.sort-desc::after{content:' ↓';}
  td{padding:7px 10px;border-bottom:1px solid #f4f4f2;vertical-align:top;}
  tr:hover td{background:#fafaf8;}
  tr.expanded td{background:#f8f8f6;}
  .db-price{font-family:'DM Mono',monospace;white-space:nowrap;}
  .db-co-matched{color:#111;font-weight:600;}
  .db-pagination{padding:10px 14px;border-top:1px solid #e0e0da;display:flex;align-items:center;gap:8px;font-size:12px;color:#6b6b6b;}
  .db-pagination button{padding:4px 10px;font-size:11px;font-family:inherit;border:1px solid #e0e0da;border-radius:4px;background:none;cursor:pointer;}
  .db-pagination button:disabled{opacity:.4;cursor:default;}
  .db-row-detail{display:none;background:#f8f8f6;padding:10px;font-size:11px;}
  .db-row-detail.open{display:table-row;}
  .db-row-detail td{padding:10px;color:#6b6b6b;}
  .db-detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px 16px;}
  .db-detail-row{display:flex;gap:6px;}
  .db-detail-row .dl{color:#999;min-width:100px;}
  .db-detail-row .dv{font-weight:500;}
</style>

<div id="dashboard-tab">

  <div class="db-header">
    <h2>CORES + GETTEL Transaction Dashboard</h2>
    <div class="db-kpis">
      <div class="db-kpi"><div class="kv" id="db-k-txns">—</div><div class="kl">Transactions</div></div>
      <div class="db-kpi"><div class="kv" id="db-k-vol">—</div><div class="kl">Total Volume</div></div>
      <div class="db-kpi"><div class="kv" id="db-k-avg">—</div><div class="kl">Avg Deal Size</div></div>
      <div class="db-kpi"><div class="kv" id="db-k-matched">—</div><div class="kl">CORES Matches</div></div>
    </div>
  </div>

  <div class="db-body">

    <div class="db-sidebar" id="db-sidebar">
      <h3>Property Class</h3>
      <div class="db-cb-group" id="db-f-class"></div>

      <h3>Property Type</h3>
      <div class="db-cb-group" id="db-f-type"></div>

      <h3>Ownership Type</h3>
      <div class="db-cb-group" id="db-f-own"></div>

      <h3>City</h3>
      <select class="db-select" id="db-f-city"><option value="">All Cities</option></select>

      <h3>Year Range</h3>
      <div class="db-range-row">
        <input class="db-range-input" id="db-f-year-from" type="number" placeholder="From">
        <span>–</span>
        <input class="db-range-input" id="db-f-year-to"   type="number" placeholder="To">
      </div>

      <h3>Price Range ($)</h3>
      <div class="db-range-row">
        <input class="db-range-input" id="db-f-price-from" type="number" placeholder="Min">
        <span>–</span>
        <input class="db-range-input" id="db-f-price-to"   type="number" placeholder="Max">
      </div>

      <h3>Subdivision</h3>
      <select class="db-select" id="db-f-subdiv"><option value="">All Subdivisions</option></select>

      <h3>Company Search</h3>
      <input class="db-text-input" id="db-f-company" placeholder="Search vendor or purchaser…">

      <h3>Person Search</h3>
      <input class="db-text-input" id="db-f-person" placeholder="Search director/shareholder…">

      <label class="db-cores-row">
        <input type="checkbox" id="db-f-cores-only"> CORES matches only
      </label>

      <button class="db-reset-btn" onclick="DB_resetAll()">Reset All Filters</button>
    </div>

    <div class="db-main">
      <div class="db-charts-row">
        <div class="db-chart-card">
          <h4>Volume by Year</h4>
          <div class="db-chart-wrap"><canvas id="db-chart-year"></canvas></div>
        </div>
        <div class="db-chart-card">
          <h4>By Property Class</h4>
          <div class="db-chart-wrap"><canvas id="db-chart-class"></canvas></div>
        </div>
      </div>
      <div class="db-charts-row">
        <div class="db-chart-card">
          <h4>Top 20 Companies</h4>
          <div class="db-chart-wrap" style="height:260px"><canvas id="db-chart-cos"></canvas></div>
        </div>
        <div class="db-chart-card">
          <h4>Top 20 People</h4>
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
              <th data-col="property_class" onclick="DB_sort('property_class')">Class</th>
              <th data-col="property_type" onclick="DB_sort('property_type')">Type</th>
              <th>Description</th>
              <th>Vendor</th>
              <th>Purchaser</th>
              <th data-col="sale_price" onclick="DB_sort('sale_price')">Price</th>
              <th data-col="unit_price" onclick="DB_sort('unit_price')">$/Unit</th>
              <th data-col="bldg_area" onclick="DB_sort('bldg_area')">Area</th>
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
const KPI0  = DB_DATA.kpis;

let DB_filtered = [...TXNS];
let DB_page_num = 1;
const DB_PAGE_SIZE = 50;
let DB_sort_col = 'sale_date';
let DB_sort_dir = 'desc';

let DB_charts = {};

function fmtPrice(v){
  if(v==null||v===''||v===undefined) return '—';
  v = parseFloat(v);
  if(isNaN(v)) return '—';
  if(v>=1e9) return '$'+(v/1e9).toFixed(2)+'B';
  if(v>=1e6) return '$'+(v/1e6).toFixed(1)+'M';
  if(v>=1e3) return '$'+(v/1e3).toFixed(0)+'K';
  return '$'+v.toLocaleString();
}

function fmtArea(v,u){return v?(parseFloat(v)||0).toLocaleString()+' '+(u||''):'—';}

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

buildCBGroup('db-f-class', FOPTS.property_classes, DB_applyFilters);
buildCBGroup('db-f-type',  FOPTS.property_types,   DB_applyFilters);
buildCBGroup('db-f-own',   FOPTS.ownership_types,  DB_applyFilters);

const cityEl = document.getElementById('db-f-city');
FOPTS.cities.sort().forEach(c=>{const o=document.createElement('option');o.value=c;o.textContent=c;cityEl.appendChild(o);});
cityEl.addEventListener('change', DB_applyFilters);

const subdivEl = document.getElementById('db-f-subdiv');
FOPTS.subdivisions.sort().forEach(s=>{const o=document.createElement('option');o.value=s;o.textContent=s;subdivEl.appendChild(o);});
subdivEl.addEventListener('change', DB_applyFilters);

['db-f-year-from','db-f-year-to','db-f-price-from','db-f-price-to','db-f-company','db-f-person'].forEach(id=>{
  document.getElementById(id).addEventListener('input', DB_applyFilters);
});
document.getElementById('db-f-cores-only').addEventListener('change', DB_applyFilters);

// Set default year bounds
const years = FOPTS.years.filter(y=>y);
if(years.length){
  document.getElementById('db-f-year-from').placeholder = Math.min(...years);
  document.getElementById('db-f-year-to').placeholder   = Math.max(...years);
}

// ─── FILTER LOGIC ────────────────────────────────────────────────────────────
function getChecked(containerId){
  return [...document.querySelectorAll(`#${containerId} input[type=checkbox]:checked`)].map(el=>el.value);
}

function DB_applyFilters(){
  const classes  = getChecked('db-f-class');
  const types    = getChecked('db-f-type');
  const owns     = getChecked('db-f-own');
  const city     = document.getElementById('db-f-city').value;
  const subdiv   = document.getElementById('db-f-subdiv').value;
  const yFrom    = parseInt(document.getElementById('db-f-year-from').value)||0;
  const yTo      = parseInt(document.getElementById('db-f-year-to').value)||9999;
  const pFrom    = parseFloat(document.getElementById('db-f-price-from').value)||0;
  const pTo      = parseFloat(document.getElementById('db-f-price-to').value)||Infinity;
  const coQ      = document.getElementById('db-f-company').value.toLowerCase();
  const peQ      = document.getElementById('db-f-person').value.toLowerCase();
  const coresOnly= document.getElementById('db-f-cores-only').checked;

  DB_filtered = TXNS.filter(t=>{
    if(!classes.includes(t.property_class)) return false;
    if(!types.includes(t.property_type))   return false;
    if(owns.length && !owns.includes(t.ownership_type)) return false;
    if(city   && t.city !== city)           return false;
    if(subdiv && t.subdivision !== subdiv)  return false;
    const yr = parseInt(t.sale_year)||0;
    if(yFrom && yr < yFrom) return false;
    if(yTo<9999 && yr > yTo) return false;
    const pr = parseFloat(t.sale_price)||0;
    if(pFrom && pr < pFrom) return false;
    if(pTo<Infinity && pr > pTo) return false;
    if(coQ && !(t.vendor_entity||'').toLowerCase().includes(coQ) &&
             !(t.purchaser_entity||'').toLowerCase().includes(coQ)) return false;
    if(peQ && !(t.vendor_person||'').toLowerCase().includes(peQ) &&
             !(t.purchaser_person||'').toLowerCase().includes(peQ)) return false;
    if(coresOnly && !t.vendor_can && !t.purchaser_can) return false;
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
  const matched = DB_filtered.filter(t=>t.vendor_can||t.purchaser_can).length;
  document.getElementById('db-k-txns').textContent    = DB_filtered.length.toLocaleString();
  document.getElementById('db-k-vol').textContent     = fmtPrice(vol);
  document.getElementById('db-k-avg').textContent     = fmtPrice(avg);
  document.getElementById('db-k-matched').textContent = matched.toLocaleString();
  document.getElementById('db-table-title').textContent = `Transactions (${DB_filtered.length.toLocaleString()})`;
}

// ─── CHARTS ──────────────────────────────────────────────────────────────────
const GREY_PALETTE = ['#111','#333','#555','#777','#999','#bbb','#ccc','#ddd'];
const ACCENT_COLOR = '#3a7bd5';

function updateCharts(){
  updateYearChart();
  updateClassChart();
  updateCosChart();
  updatePeopleChart();
}

function updateYearChart(){
  const yearClass = {};
  DB_filtered.forEach(t=>{
    const y = t.sale_year||'Unknown';
    const c = t.property_class||'Unknown';
    if(!yearClass[y]) yearClass[y]={};
    yearClass[y][c] = (yearClass[y][c]||0)+(parseFloat(t.sale_price)||0);
  });
  const years   = Object.keys(yearClass).sort();
  const classes = [...new Set(DB_filtered.map(t=>t.property_class))].filter(Boolean);
  const datasets= classes.map((cls,i)=>({
    label:cls,
    data:years.map(y=>(yearClass[y]||{})[cls]||0),
    backgroundColor: GREY_PALETTE[i%GREY_PALETTE.length],
    stack:'s',
  }));

  if(DB_charts.year){
    DB_charts.year.data.labels=years;
    DB_charts.year.data.datasets=datasets;
    DB_charts.year.update();
  } else {
    DB_charts.year = new Chart(document.getElementById('db-chart-year'),{
      type:'bar',
      data:{labels:years,datasets},
      options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false},tooltip:{callbacks:{
          label:ctx=>`${ctx.dataset.label}: ${fmtPrice(ctx.raw)}`
        }}},
        scales:{x:{stacked:true},y:{stacked:true,ticks:{callback:v=>fmtPrice(v)}}},
      }
    });
  }
}

function updateClassChart(){
  const classTotals = {};
  DB_filtered.forEach(t=>{
    const c = t.property_class||'Unknown';
    classTotals[c]=(classTotals[c]||0)+(parseFloat(t.sale_price)||0);
  });
  const entries = Object.entries(classTotals).sort((a,b)=>b[1]-a[1]);
  const labels  = entries.map(e=>e[0]);
  const data    = entries.map(e=>e[1]);

  if(DB_charts.cls){
    DB_charts.cls.data.labels=labels;
    DB_charts.cls.data.datasets[0].data=data;
    DB_charts.cls.update();
  } else {
    DB_charts.cls = new Chart(document.getElementById('db-chart-class'),{
      type:'doughnut',
      data:{labels,datasets:[{data,backgroundColor:GREY_PALETTE}]},
      options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{position:'right',labels:{font:{size:11}}},
          tooltip:{callbacks:{label:ctx=>`${ctx.label}: ${fmtPrice(ctx.raw)} (${(ctx.raw/data.reduce((s,v)=>s+v,0)*100).toFixed(1)}%)`}}}
      }
    });
  }
}

function updateCosChart(){
  const coCount = {};
  DB_filtered.forEach(t=>{
    const ve = t.vendor_entity; const pe = t.purchaser_entity;
    if(ve) coCount[ve]=(coCount[ve]||{count:0,matched:!!t.vendor_can}).count++||0, coCount[ve].count++;
    if(pe) coCount[pe]=(coCount[pe]||{count:0,matched:!!t.purchaser_can}).count++||0, coCount[pe].count++;
  });
  const sorted = Object.entries(coCount).sort((a,b)=>b[1].count-a[1].count).slice(0,20);
  const labels = sorted.map(e=>e[0].length>30?e[0].slice(0,28)+'…':e[0]);
  const data   = sorted.map(e=>e[1].count);
  const colors = sorted.map(e=>e[1].matched?'#111':'#aaa');

  if(DB_charts.cos){
    DB_charts.cos.data.labels=labels;
    DB_charts.cos.data.datasets[0].data=data;
    DB_charts.cos.data.datasets[0].backgroundColor=colors;
    DB_charts.cos.update();
  } else {
    DB_charts.cos = new Chart(document.getElementById('db-chart-cos'),{
      type:'bar',
      data:{labels,datasets:[{data,backgroundColor:colors,borderWidth:0}]},
      options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false}},
        scales:{x:{ticks:{stepSize:1}},y:{ticks:{font:{size:10}}}},
      }
    });
  }
}

function updatePeopleChart(){
  const peCount = {};
  DB_filtered.forEach(t=>{
    const vp = t.vendor_person; const pp = t.purchaser_person;
    if(vp) peCount[vp]=(peCount[vp]||{count:0,cos:new Set()}), peCount[vp].count++, peCount[vp].cos.add(t.vendor_entity);
    if(pp) peCount[pp]=(peCount[pp]||{count:0,cos:new Set()}), peCount[pp].count++, peCount[pp].cos.add(t.purchaser_entity);
  });
  const sorted = Object.entries(peCount).sort((a,b)=>b[1].count-a[1].count).slice(0,20);
  const labels = sorted.map(e=>e[0]);
  const data   = sorted.map(e=>e[1].count);

  if(DB_charts.ppl){
    DB_charts.ppl.data.labels=labels;
    DB_charts.ppl.data.datasets[0].data=data;
    DB_charts.ppl.update();
  } else {
    DB_charts.ppl = new Chart(document.getElementById('db-chart-people'),{
      type:'bar',
      data:{labels,datasets:[{data,backgroundColor:'#555',borderWidth:0}]},
      options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false}},
        scales:{x:{ticks:{stepSize:1}},y:{ticks:{font:{size:10}}}},
      }
    });
  }
}

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
    const tr = document.createElement('tr');
    tr.style.cursor='pointer';
    tr.innerHTML=`
      <td>${n}</td>
      <td>${t.sale_date||'—'}</td>
      <td>${t.city||'—'}</td>
      <td style="white-space:nowrap">${(t.property_class||'').slice(0,8)}</td>
      <td>${t.property_type||'—'}</td>
      <td title="${t.description||''}">${(t.description||'').slice(0,22)}</td>
      <td class="${vMatch}" title="${t.vendor_entity||''}">${(t.vendor_entity||'—').slice(0,22)}</td>
      <td class="${pMatch}" title="${t.purchaser_entity||''}">${(t.purchaser_entity||'—').slice(0,22)}</td>
      <td class="db-price">${fmtPrice(t.sale_price)}</td>
      <td class="db-price">${t.unit_price?fmtPrice(t.unit_price):'—'}</td>
      <td>${fmtArea(t.bldg_area||t.site_area, t.bldg_units||t.site_units)}</td>`;
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
      <div class="db-detail-row"><span class="dl">Vendor</span><span class="dv">${t.vendor_entity||'—'}${t.vendor_person?' · '+t.vendor_role+': '+t.vendor_person:''}${t.vendor_can?' [CORES '+t.vendor_can+']':''}</span></div>
      <div class="db-detail-row"><span class="dl">Purchaser</span><span class="dv">${t.purchaser_entity||'—'}${t.purchaser_person?' · '+t.purchaser_role+': '+t.purchaser_person:''}${t.purchaser_can?' [CORES '+t.purchaser_can+']':''}</span></div>
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
  document.querySelectorAll('#db-f-class input, #db-f-type input, #db-f-own input').forEach(el=>el.checked=true);
  ['db-f-city','db-f-subdiv'].forEach(id=>document.getElementById(id).value='');
  ['db-f-year-from','db-f-year-to','db-f-price-from','db-f-price-to','db-f-company','db-f-person'].forEach(id=>document.getElementById(id).value='');
  document.getElementById('db-f-cores-only').checked=false;
  DB_applyFilters();
};

window.DB_exportCSV = function(){
  const cols = ['txn_id','sale_date','city','property_class','property_type','ownership_type',
    'description','address','vendor_entity','vendor_person','vendor_role','vendor_can',
    'purchaser_entity','purchaser_person','purchaser_role','purchaser_can',
    'sale_price','unit_price','bldg_area','site_area','year_built','subdivision'];
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
