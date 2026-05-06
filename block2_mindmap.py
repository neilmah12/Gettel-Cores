# @title 2 — NETWORK MIND MAP (HTML)
# Input: graph_data.json
# Output: mindmap_section.html

import json

with open("graph_data.json","r",encoding="utf-8") as f:
    graph_data = f.read()

html = r"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
  :root{--bg:#f8f8f6;--surface:#fff;--border:#e0e0da;--text:#1a1a1a;--muted:#6b6b6b;
    --accent:#111;--cores-col:#111;--gettel-col:#3a7bd5;--both-col:#6b21a8;
    --depth1:#111;--depth2:#444;--depth3:#777;--person:#fff;--other:#faf5eb;}
  *{box-sizing:border-box;margin:0;padding:0;}
  body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text);height:100vh;overflow:hidden;}
  .mm-app{display:grid;grid-template-columns:280px 1fr 320px;height:100vh;}

  .mm-sb{background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden;}
  .mm-sb-header{padding:14px 16px 0;border-bottom:1px solid var(--border);}
  .mm-sb-header h2{font-size:13px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);margin-bottom:10px;}
  .mm-sb-tabs{display:flex;gap:0;border-bottom:1px solid var(--border);}
  .mm-sb-tab{flex:1;padding:8px 0;font-size:12px;font-weight:500;border:none;background:none;cursor:pointer;color:var(--muted);border-bottom:2px solid transparent;}
  .mm-sb-tab.active{color:var(--text);border-bottom-color:var(--accent);}
  .mm-filters{padding:10px 12px;border-bottom:1px solid var(--border);display:flex;flex-direction:column;gap:6px;}
  .mm-filters input,.mm-filters select{width:100%;padding:5px 8px;font-size:12px;font-family:inherit;border:1px solid var(--border);border-radius:4px;background:var(--bg);color:var(--text);}
  .mm-filters-row{display:flex;gap:6px;}
  .mm-filters-row input{flex:1;}
  .btn-reset{padding:4px 8px;font-size:11px;font-family:inherit;border:1px solid var(--border);border-radius:4px;background:none;cursor:pointer;color:var(--muted);}
  .btn-reset:hover{background:var(--bg);}
  .mm-list{flex:1;overflow-y:auto;padding:6px 0;}
  .mm-list-item{padding:8px 14px;cursor:pointer;border-left:3px solid transparent;font-size:12px;line-height:1.4;}
  .mm-list-item:hover{background:#f4f4f2;}
  .mm-list-item.active{border-left-color:var(--accent);background:#f4f4f2;}
  .mm-list-item .li-name{font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  .mm-list-item .li-meta{color:var(--muted);font-size:11px;display:flex;gap:6px;margin-top:2px;}
  .mm-list-count{padding:6px 14px;font-size:11px;color:var(--muted);}

  .mm-canvas{position:relative;overflow:hidden;background:var(--bg);}
  #mm-svg{width:100%;height:100%;}
  .mm-ctrl{position:absolute;bottom:16px;right:16px;display:flex;flex-direction:column;gap:4px;}
  .mm-ctrl button{width:32px;height:32px;border:1px solid var(--border);background:var(--surface);border-radius:4px;cursor:pointer;font-size:14px;display:flex;align-items:center;justify-content:center;}
  .mm-ctrl button:hover{background:var(--bg);}
  .mm-empty{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;color:var(--muted);}
  .mm-empty .e-icon{font-size:40px;margin-bottom:8px;}
  .mm-empty p{font-size:13px;}
  .mm-legend{position:absolute;bottom:16px;left:16px;background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:8px 12px;font-size:11px;}
  .mm-legend-row{display:flex;align-items:center;gap:6px;margin-bottom:4px;}
  .mm-legend-row:last-child{margin-bottom:0;}
  .l-dot{width:10px;height:10px;border-radius:50%;display:inline-block;flex-shrink:0;}

  .mm-detail{background:var(--surface);border-left:1px solid var(--border);overflow-y:auto;font-size:12px;}
  .mm-detail-empty{display:flex;align-items:center;justify-content:center;height:100%;color:var(--muted);font-size:13px;}
  .mm-detail-inner{padding:16px;}
  .d-name{font-size:15px;font-weight:600;line-height:1.3;margin-bottom:8px;}
  .d-badges{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:12px;}
  .badge{padding:2px 7px;border-radius:10px;font-size:10px;font-weight:600;letter-spacing:.03em;text-transform:uppercase;}
  .badge-active{background:#d1fae5;color:#065f46;}
  .badge-dissolved{background:#fee2e2;color:#991b1b;}
  .badge-cores{background:#111;color:#fff;}
  .badge-gettel{background:#dbeafe;color:#1d4ed8;}
  .badge-both{background:#ede9fe;color:#5b21b6;}
  .badge-d1{background:#111;color:#fff;}
  .badge-d2{background:#444;color:#fff;}
  .badge-d3{background:#777;color:#fff;}
  .d-section{margin-top:14px;}
  .d-section-title{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);border-bottom:1px solid var(--border);padding-bottom:4px;margin-bottom:8px;}
  .d-row{display:flex;gap:8px;margin-bottom:4px;}
  .d-row .lbl{color:var(--muted);min-width:90px;flex-shrink:0;}
  .d-row .val{font-weight:500;word-break:break-word;}
  .member-row{padding:6px 0;border-bottom:1px solid var(--border);cursor:pointer;}
  .member-row:last-child{border-bottom:none;}
  .member-row:hover{background:#fafaf8;}
  .member-name{font-weight:500;}
  .member-meta{color:var(--muted);font-size:11px;margin-top:1px;}
  .txn-row{padding:6px 0;border-bottom:1px solid var(--border);cursor:pointer;}
  .txn-row:last-child{border-bottom:none;}
  .txn-row:hover .txn-header{text-decoration:underline;}
  .txn-header{display:flex;justify-content:space-between;align-items:start;}
  .txn-price{font-weight:600;font-family:'DM Mono',monospace;white-space:nowrap;}
  .txn-desc{color:var(--muted);font-size:11px;margin-top:2px;}
  .txn-detail{display:none;background:#fafaf8;padding:8px;border-radius:4px;margin-top:4px;font-size:11px;}
  .txn-detail.open{display:block;}
  .txn-badge{font-size:10px;padding:1px 5px;border-radius:3px;font-weight:600;}
  .txn-vendor{background:#f0fdf4;color:#166534;}
  .txn-purchaser{background:#eff6ff;color:#1e40af;}

  .node circle{stroke:#333;stroke-width:1.5px;cursor:pointer;}
  .node text{font-family:'DM Sans',sans-serif;font-size:11px;pointer-events:none;}
  .node .txn-badge-svg{font-family:'DM Mono',monospace;font-size:9px;fill:#555;}
  .link{fill:none;stroke:#ccc;stroke-width:1px;}
  .collapsed-indicator{fill:#999;font-size:10px;cursor:pointer;}
</style>

<div id="mindmap-tab">
<div class="mm-app">

  <div class="mm-sb">
    <div class="mm-sb-header">
      <h2>CORES + GETTEL Network</h2>
      <div class="mm-sb-tabs">
        <button class="mm-sb-tab active" data-tab="companies" onclick="MM_switchTab('companies')">Companies</button>
        <button class="mm-sb-tab" data-tab="people" onclick="MM_switchTab('people')">People</button>
      </div>
    </div>

    <div id="mm-co-filters" class="mm-filters">
      <input id="mm-f-co" placeholder="Search company…" oninput="MM_filterCompanies()">
      <div class="mm-filters-row">
        <select id="mm-f-status" onchange="MM_filterCompanies()">
          <option value="">All statuses</option>
          <option>Active</option><option>Dissolved</option>
        </select>
        <select id="mm-f-source" onchange="MM_filterCompanies()">
          <option value="">All sources</option>
          <option value="cores">CORES</option>
          <option value="gettel_only">Gettel Only</option>
          <option value="cores+gettel">Both</option>
        </select>
      </div>
      <div class="mm-filters-row">
        <select id="mm-f-depth" onchange="MM_filterCompanies()">
          <option value="">All depths</option>
          <option value="1">Depth 1</option>
          <option value="2">Depth 2</option>
          <option value="3">Depth 3</option>
        </select>
        <input id="mm-f-mintxn" type="number" min="0" placeholder="Min txns" oninput="MM_filterCompanies()">
      </div>
      <button class="btn-reset" onclick="MM_resetCoFilters()">Reset</button>
    </div>

    <div id="mm-pe-filters" class="mm-filters" style="display:none">
      <input id="mm-f-person" placeholder="Search person…" oninput="MM_filterPeople()">
      <div class="mm-filters-row">
        <select id="mm-f-role" onchange="MM_filterPeople()">
          <option value="">All roles</option>
          <option>Director</option><option>Shareholder</option>
        </select>
        <input id="mm-f-mincos" type="number" min="0" placeholder="Min cos" oninput="MM_filterPeople()">
      </div>
      <button class="btn-reset" onclick="MM_resetPeFilters()">Reset</button>
    </div>

    <div id="mm-list-count" class="mm-list-count"></div>
    <div id="mm-co-list" class="mm-list"></div>
    <div id="mm-pe-list" class="mm-list" style="display:none"></div>
  </div>

  <div class="mm-canvas" id="mm-canvas">
    <svg id="mm-svg"></svg>
    <div class="mm-empty" id="mm-empty">
      <div class="e-icon">🏢</div>
      <p>Select a company to explore its network</p>
    </div>
    <div class="mm-ctrl">
      <button title="Zoom in" onclick="MM_zoom(1.3)">+</button>
      <button title="Zoom out" onclick="MM_zoom(0.77)">−</button>
      <button title="Fit" onclick="MM_fit()" style="font-size:11px">Fit</button>
      <button title="Expand all" onclick="MM_expandAll()" style="font-size:11px">Exp</button>
      <button title="Collapse all" onclick="MM_collapseAll()" style="font-size:11px">Col</button>
    </div>
    <div class="mm-legend">
      <div class="mm-legend-row"><span class="l-dot" style="background:#111"></span>CORES company</div>
      <div class="mm-legend-row"><span class="l-dot" style="background:#3a7bd5"></span>Gettel only</div>
      <div class="mm-legend-row"><span class="l-dot" style="background:#fff;border:1.5px solid #111"></span>Individual</div>
      <div class="mm-legend-row"><span class="l-dot" style="background:#faf5eb;border:1.5px solid #aaa"></span>Other (trust/jointly)</div>
    </div>
  </div>

  <div class="mm-detail" id="mm-detail">
    <div class="mm-detail-empty">Click a node to see details</div>
  </div>

</div>
</div>

<script>
(function(){
const MM_DATA = """ + graph_data + r""";

const CI = MM_DATA.company_info;
const CL = MM_DATA.company_list;
const PI = MM_DATA.person_index;

let MM_activeTab = 'companies';
let MM_selectedCAN = null;
let MM_collapsed = new Set();
let MM_svg, MM_g, MM_zoomBeh;
let MM_currentD3Data = null;
let MM_filteredCos = [...CL];
let MM_filteredPe = Object.entries(PI);

function fmtPrice(v){
  if(!v) return '—';
  if(v>=1e9) return '$'+(v/1e9).toFixed(2)+'B';
  if(v>=1e6) return '$'+(v/1e6).toFixed(1)+'M';
  if(v>=1e3) return '$'+(v/1e3).toFixed(0)+'K';
  return '$'+v.toLocaleString();
}

window.MM_switchTab = function(tab){
  MM_activeTab = tab;
  document.querySelectorAll('.mm-sb-tab').forEach(b=>b.classList.toggle('active', b.dataset.tab===tab));
  document.getElementById('mm-co-filters').style.display = tab==='companies'?'':'none';
  document.getElementById('mm-pe-filters').style.display = tab==='people'?'':'none';
  document.getElementById('mm-co-list').style.display    = tab==='companies'?'':'none';
  document.getElementById('mm-pe-list').style.display    = tab==='people'?'':'none';
  if(tab==='companies') renderCoList();
  else renderPeList();
};

window.MM_filterCompanies = function(){
  const q    = document.getElementById('mm-f-co').value.toLowerCase();
  const stat = document.getElementById('mm-f-status').value;
  const src  = document.getElementById('mm-f-source').value;
  const dep  = document.getElementById('mm-f-depth').value;
  const minT = parseInt(document.getElementById('mm-f-mintxn').value)||0;
  MM_filteredCos = CL.filter(c=>{
    if(q && !c.label.toLowerCase().includes(q)) return false;
    if(stat && c.status !== stat) return false;
    if(src && c.source !== src) return false;
    if(dep && String(c.depth) !== dep) return false;
    if(c.txn_count < minT) return false;
    return true;
  });
  renderCoList();
};

window.MM_resetCoFilters = function(){
  ['mm-f-co','mm-f-mintxn'].forEach(id=>document.getElementById(id).value='');
  ['mm-f-status','mm-f-source','mm-f-depth'].forEach(id=>document.getElementById(id).value='');
  MM_filterCompanies();
};

window.MM_filterPeople = function(){
  const q    = document.getElementById('mm-f-person').value.toLowerCase();
  const role = document.getElementById('mm-f-role').value.toLowerCase();
  const minC = parseInt(document.getElementById('mm-f-mincos').value)||0;
  MM_filteredPe = Object.entries(PI).filter(([k,p])=>{
    if(q && !p.label.toLowerCase().includes(q)) return false;
    if(minC && p.companies.length < minC) return false;
    return true;
  });
  renderPeList();
};

window.MM_resetPeFilters = function(){
  ['mm-f-person','mm-f-mincos'].forEach(id=>document.getElementById(id).value='');
  document.getElementById('mm-f-role').value='';
  MM_filterPeople();
};

function renderCoList(){
  const el = document.getElementById('mm-co-list');
  document.getElementById('mm-list-count').textContent = MM_filteredCos.length+' companies';
  const CHUNK = 100;
  let rendered = 0;
  el.innerHTML='';
  function addChunk(){
    const slice = MM_filteredCos.slice(rendered, rendered+CHUNK);
    slice.forEach(c=>{
      const div = document.createElement('div');
      div.className='mm-list-item'+(c.can===MM_selectedCAN?' active':'');
      div.innerHTML=`<div class="li-name">${c.label||c.can}</div>
        <div class="li-meta">
          <span>${c.status||'—'}</span>
          <span>${sourceBadgeText(c.source)}</span>
          ${c.txn_count>0?`<span>📊 ${c.txn_count}</span>`:''}
        </div>`;
      div.onclick=()=>MM_selectCompany(c.can);
      el.appendChild(div);
    });
    rendered+=slice.length;
    if(rendered<MM_filteredCos.length){
      el.addEventListener('scroll',function onScroll(){
        if(el.scrollTop+el.clientHeight > el.scrollHeight-40){
          el.removeEventListener('scroll',onScroll);
          addChunk();
        }
      },{once:true});
    }
  }
  addChunk();
}

function renderPeList(){
  const el = document.getElementById('mm-pe-list');
  document.getElementById('mm-list-count').textContent = MM_filteredPe.length+' people';
  el.innerHTML='';
  MM_filteredPe.slice(0,200).forEach(([key,p])=>{
    const div = document.createElement('div');
    div.className='mm-list-item';
    div.innerHTML=`<div class="li-name">${p.label}</div>
      <div class="li-meta">
        <span>${p.companies.length} co${p.companies.length!==1?'s':''}</span>
        <span>${p.transactions.length} txns</span>
      </div>`;
    div.onclick=()=>MM_selectPerson(key);
    el.appendChild(div);
  });
}

function sourceBadgeText(s){
  if(s==='cores') return 'CORES';
  if(s==='gettel_only') return 'GETTEL';
  if(s==='cores+gettel') return 'CORES+GETTEL';
  return s||'';
}

// ─── D3 TREE ────────────────────────────────────────────────────────────────
function initSvg(){
  const canvas = document.getElementById('mm-canvas');
  MM_svg = d3.select('#mm-svg');
  MM_svg.selectAll('*').remove();
  MM_zoomBeh = d3.zoom().scaleExtent([0.05,4]).on('zoom',e=>MM_g.attr('transform',e.transform));
  MM_svg.call(MM_zoomBeh);
  MM_g = MM_svg.append('g');
}

function buildHierarchy(can, visited){
  visited = visited || new Set();
  if(visited.has(can)) return null;
  visited.add(can);
  const co = CI[can];
  if(!co) return null;
  const node = {
    id: can, label: co.label||can, nodeType:'company',
    source: co.source, depth: co.depth, status: co.status,
    txnCount: (co.transactions||[]).length,
    children: [],
  };
  if(!MM_collapsed.has(can)){
    (co.children||[]).forEach(ch=>{
      if(ch.node_type==='legal entity'||ch.node_type==='legal_entity'){
        const childCAN = ch.corp_can;
        if(childCAN && CI[childCAN]){
          const sub = buildHierarchy(childCAN, visited);
          if(sub) node.children.push(sub);
        } else {
          node.children.push({id:ch.id, label:ch.label, nodeType:'company-ext',
            source:'gettel_only', depth:'-', status:'', txnCount:0, children:[]});
        }
      } else {
        node.children.push({id:ch.id, label:ch.label,
          nodeType: ch.node_type==='individual'?'person':'other',
          role:ch.role, pct:ch.pct_shares, status:ch.status,
          appointment:ch.appointment, address:ch.address, children:[]});
      }
    });
  }
  return node;
}

function drawTree(can){
  if(!MM_svg) initSvg();
  document.getElementById('mm-empty').style.display='none';
  const hierarchy = buildHierarchy(can);
  if(!hierarchy) return;
  MM_currentD3Data = {can};

  const root = d3.hierarchy(hierarchy);
  const treeLayout = d3.tree().nodeSize([34,240]);
  treeLayout(root);

  MM_g.selectAll('*').remove();

  MM_g.selectAll('.link')
    .data(root.links())
    .enter().append('path')
    .attr('class','link')
    .attr('d', d3.linkHorizontal().x(d=>d.y).y(d=>d.x));

  const node = MM_g.selectAll('.node')
    .data(root.descendants())
    .enter().append('g')
    .attr('class','node')
    .attr('transform',d=>`translate(${d.y},${d.x})`)
    .on('click',(_,d)=>MM_nodeClick(d.data));

  node.append('circle')
    .attr('r', d=>d.data.nodeType==='company'||d.data.nodeType==='company-ext'?9:6)
    .style('fill', d=>{
      const t = d.data.nodeType;
      if(t==='person') return '#fff';
      if(t==='other') return '#faf5eb';
      const s = d.data.source;
      if(s==='gettel_only') return '#3a7bd5';
      if(s==='cores+gettel') return '#6b21a8';
      const dep = String(d.data.depth);
      if(dep==='1') return '#111';
      if(dep==='2') return '#444';
      return '#777';
    })
    .style('stroke', d=>{
      if(d.data.nodeType==='person') return '#111';
      if(d.data.nodeType==='other') return '#aaa';
      return '#333';
    });

  node.append('text')
    .attr('dy','0.31em')
    .attr('x', d=>{
      const isCompany = d.data.nodeType==='company'||d.data.nodeType==='company-ext';
      return (d.children&&d.children.length>0) ? (isCompany?-13:-10) : (isCompany?13:10);
    })
    .attr('text-anchor', d=>(d.children&&d.children.length>0)?'end':'start')
    .text(d=>d.data.label.length>28?d.data.label.slice(0,26)+'…':d.data.label);

  node.filter(d=>(d.data.nodeType==='company'||d.data.nodeType==='company-ext') && d.data.txnCount>0)
    .append('text')
    .attr('class','txn-badge-svg')
    .attr('dy','-1em')
    .attr('x',0)
    .attr('text-anchor','middle')
    .text(d=>`[${d.data.txnCount}]`);

  // Collapsed indicator
  node.filter(d=>MM_collapsed.has(d.data.id))
    .append('text')
    .attr('class','collapsed-indicator')
    .attr('dy','0.31em').attr('x',13).attr('text-anchor','start')
    .text('▶');

  MM_fit();
}

window.MM_selectCompany = function(can){
  MM_selectedCAN = can;
  renderCoList();
  drawTree(can);
  showCompanyDetail(can);
};

window.MM_selectPerson = function(key){
  showPersonDetail(key);
};

function MM_nodeClick(data){
  if(data.nodeType==='company'||data.nodeType==='company-ext'){
    if(MM_collapsed.has(data.id)) MM_collapsed.delete(data.id);
    else MM_collapsed.add(data.id);
    drawTree(MM_selectedCAN);
    showCompanyDetail(data.id);
  } else {
    showPersonDetailByLabel(data.label);
  }
}

window.MM_zoom = function(factor){
  MM_svg.transition().call(MM_zoomBeh.scaleBy, factor);
};

window.MM_fit = function(){
  const canvas = document.getElementById('mm-canvas');
  const w = canvas.clientWidth, h = canvas.clientHeight;
  const bbox = MM_g.node().getBBox();
  if(!bbox||bbox.width===0) return;
  const scale = Math.min(0.9, Math.min(w/bbox.width, h/bbox.height)*0.85);
  const tx = (w-bbox.width*scale)/2 - bbox.x*scale;
  const ty = (h-bbox.height*scale)/2 - bbox.y*scale;
  MM_svg.transition().duration(400).call(MM_zoomBeh.transform, d3.zoomIdentity.translate(tx,ty).scale(scale));
};

window.MM_expandAll = function(){
  MM_collapsed.clear();
  if(MM_selectedCAN) drawTree(MM_selectedCAN);
};

window.MM_collapseAll = function(){
  if(!MM_selectedCAN) return;
  const co = CI[MM_selectedCAN];
  if(co)(co.children||[]).forEach(ch=>{if(ch.corp_can)MM_collapsed.add(ch.corp_can);});
  drawTree(MM_selectedCAN);
};

// ─── DETAIL PANEL ────────────────────────────────────────────────────────────
function showCompanyDetail(can){
  const co = CI[can];
  const el = document.getElementById('mm-detail');
  if(!co){el.innerHTML='<div class="mm-detail-empty">No data for this company.</div>';return;}

  const srcBadge = co.source==='cores'?'<span class="badge badge-cores">CORES</span>'
    : co.source==='gettel_only'?'<span class="badge badge-gettel">GETTEL</span>'
    : '<span class="badge badge-both">CORES+GETTEL</span>';
  const statBadge = co.status==='Active'?'<span class="badge badge-active">Active</span>'
    : co.status?`<span class="badge badge-dissolved">${co.status}</span>`:'';
  const depBadge = co.depth?`<span class="badge badge-d${co.depth}">Depth ${co.depth}</span>`:'';

  let html = `<div class="mm-detail-inner">
    <div class="d-name">${co.label||can}</div>
    <div class="d-badges">${statBadge}${srcBadge}${depBadge}</div>`;

  if(co.source!=='gettel_only'){
    html+=`<div class="d-section"><div class="d-section-title">Registration</div>
      <div class="d-row"><span class="lbl">CAN</span><span class="val">${co.can}</span></div>
      <div class="d-row"><span class="lbl">Type</span><span class="val">${co.le_type||'—'}</span></div>
      <div class="d-row"><span class="lbl">Corp Type</span><span class="val">${co.corp_type||'—'}</span></div>
      <div class="d-row"><span class="lbl">Reg Date</span><span class="val">${co.registration_date||'—'}</span></div>
      <div class="d-row"><span class="lbl">Last AR</span><span class="val">${co.last_ar_year||'—'} (${co.last_ar_filed||'—'})</span></div>
    </div>`;
  }

  if(co.address||co.email){
    html+=`<div class="d-section"><div class="d-section-title">Address</div>
      <div class="d-row"><span class="lbl">Address</span><span class="val">${co.address||'—'}</span></div>
      ${co.email?`<div class="d-row"><span class="lbl">Email</span><span class="val">${co.email}</span></div>`:''}
      ${co.agent?`<div class="d-row"><span class="lbl">Agent</span><span class="val">${co.agent}</span></div>`:''}
    </div>`;
  }

  const members = co.children||[];
  if(members.length){
    html+=`<div class="d-section"><div class="d-section-title">Members (${members.length})</div>`;
    members.forEach(m=>{
      html+=`<div class="member-row">
        <div class="member-name">${m.label}</div>
        <div class="member-meta">${m.role}${m.pct_shares?' · '+m.pct_shares+'%':''}${m.status?' · '+m.status:''}</div>
      </div>`;
    });
    html+='</div>';
  }

  const txns = co.transactions||[];
  if(txns.length){
    html+=`<div class="d-section"><div class="d-section-title">Transactions (${txns.length})</div>`;
    txns.sort((a,b)=>b.sale_date>a.sale_date?1:-1).forEach((t,i)=>{
      const roleCls = t.role==='vendor'?'txn-vendor':'txn-purchaser';
      html+=`<div class="txn-row" onclick="MM_toggleTxn('txn-${i}-${can}')">
        <div class="txn-header">
          <span><span class="txn-badge ${roleCls}">${t.role.toUpperCase()}</span> ${t.sale_date||'—'}</span>
          <span class="txn-price">${fmtPrice(t.sale_price)}</span>
        </div>
        <div class="txn-desc">${t.description||''} · ${t.city||''}</div>
        <div class="txn-detail" id="txn-${i}-${can}">
          <div class="d-row"><span class="lbl">Address</span><span class="val">${t.address||'—'}</span></div>
          <div class="d-row"><span class="lbl">Class</span><span class="val">${t.property_class||'—'}</span></div>
          <div class="d-row"><span class="lbl">$/Unit</span><span class="val">${t.unit_price?fmtPrice(t.unit_price):'—'}</span></div>
          <div class="d-row"><span class="lbl">Bldg Area</span><span class="val">${t.bldg_area?t.bldg_area.toLocaleString()+' '+t.bldg_units:'—'}</span></div>
          <div class="d-row"><span class="lbl">Site Area</span><span class="val">${t.site_area?t.site_area.toLocaleString()+' '+t.site_units:'—'}</span></div>
          <div class="d-row"><span class="lbl">Year Built</span><span class="val">${t.year_built||'—'}</span></div>
          <div class="d-row"><span class="lbl">Counterparty</span><span class="val">${t.counterparty||'—'}${t.counterparty_person?' · '+t.counterparty_person:''}</span></div>
        </div>
      </div>`;
    });
    html+='</div>';
  }

  html+='</div>';
  el.innerHTML=html;
}

window.MM_toggleTxn = function(id){
  const el = document.getElementById(id);
  if(el) el.classList.toggle('open');
};

function showPersonDetail(key){
  const p = PI[key];
  const el = document.getElementById('mm-detail');
  if(!p){el.innerHTML='<div class="mm-detail-empty">Person not found.</div>';return;}
  let html = `<div class="mm-detail-inner">
    <div class="d-name">${p.label}</div>
    <div class="d-section"><div class="d-section-title">Companies (${p.companies.length})</div>`;
  p.companies.forEach(can=>{
    const co = CI[can];
    html+=`<div class="member-row" onclick="MM_selectCompany('${can}')">
      <div class="member-name">${co?co.label:can}</div>
      <div class="member-meta">${co?co.status||'':''}</div>
    </div>`;
  });
  html+='</div>';
  if(p.transactions.length){
    const byConf = {high_direct:[], medium_cores:[], low_name:[]};
    p.transactions.forEach(t=>(byConf[t.confidence]||[]).push(t));
    html+=`<div class="d-section"><div class="d-section-title">Transactions (${p.transactions.length})</div>`;
    ['high_direct','medium_cores','low_name'].forEach(conf=>{
      if(!byConf[conf].length) return;
      html+=`<div style="font-size:11px;color:var(--muted);margin:6px 0 3px;font-weight:600;">${conf.replace('_',' ').toUpperCase()}</div>`;
      byConf[conf].forEach(t=>{
        const txn = MM_DATA.company_info;
        const co = CI[t.company_can];
        html+=`<div class="txn-row">
          <div class="txn-header">
            <span>${co?co.label:t.company_can}</span>
            <span class="txn-badge ${t.role==='vendor'?'txn-vendor':'txn-purchaser'}">${(t.role||'').toUpperCase()}</span>
          </div>
        </div>`;
      });
    });
    html+='</div>';
  }
  html+='</div>';
  el.innerHTML=html;
}

function showPersonDetailByLabel(label){
  const key = Object.keys(PI).find(k=>PI[k].label===label);
  if(key) showPersonDetail(key);
  else{
    document.getElementById('mm-detail').innerHTML=
      `<div class="mm-detail-inner"><div class="d-name">${label}</div>
       <div style="color:var(--muted);font-size:12px;margin-top:8px;">Not in CORES person index.</div></div>`;
  }
}

// ─── INIT ────────────────────────────────────────────────────────────────────
MM_filteredCos = [...CL];
MM_filteredPe  = Object.entries(PI);
renderCoList();
initSvg();

})();
</script>
"""

with open("mindmap_section.html","w",encoding="utf-8") as f:
    f.write(html)

print("mindmap_section.html written.")
print(f"  File size: {len(html)/1024:.0f} KB (excluding embedded data)")
