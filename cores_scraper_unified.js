// ============================================================
// CORES UNIFIED SCRAPER — Phase 1 + Phase 2
// Paste into Chrome DevTools Console (select TOP frame context)
// Supports: Normal mode (confirm between phases) or Overnight mode (fully automatic)
// Anti-block: jitter delays, long pauses every N companies, exponential backoff
// Resume: progress auto-saved to localStorage under key "cores_progress"
// ============================================================

(function () {

// ── CONFIG ───────────────────────────────────────────────────
const CFG = {
  // Normal mode delays (ms)
  betweenDirectors:    1200,
  betweenSteps:        1000,
  betweenCompanies:    2000,
  afterSearch:         2500,

  // Overnight mode multiplier (applied on top of normal delays)
  overnightMultiplier: 2.0,

  // Jitter: adds ±X ms randomly to every delay
  jitterMs:            600,

  // Long pause: every N companies, pause for longPauseMs
  longPauseEveryN:     25,
  longPauseMs:         45000,   // 45s — mimics a human stepping away
  longPauseMsOvernight: 90000,  // 90s in overnight mode

  // Retry / backoff
  maxRetries:          3,
  backoffBaseMs:       4000,    // 4s, then 8s, then 16s (exponential)

  // Navigation timeout
  navTimeoutMs:        20000,

  BASE: 'https://cores.reg.gov.ab.ca/cores/cr',
};

// ── STATE ────────────────────────────────────────────────────
let overnightMode = false;
let p1Companies   = [];
let p1Directors   = [];
let p2Companies   = [];
let p2Directors   = [];

// ── UTILS ────────────────────────────────────────────────────
const sleep = ms => new Promise(r => setTimeout(r, ms));

function jitter(ms) {
  const j = Math.floor((Math.random() * 2 - 1) * CFG.jitterMs);
  const base = overnightMode ? Math.round(ms * CFG.overnightMultiplier) : ms;
  return Math.max(200, base + j);
}

async function pause(ms) {
  await sleep(jitter(ms));
}

function getFrame(name) {
  if (name === 'bottom' && document.querySelectorAll('frame').length === 0) return window;
  for (const f of document.querySelectorAll('frame')) {
    if (f.name === name) return f.contentWindow;
  }
  return null;
}

function getSpuId() {
  const selfMatch = window.location.href.match(/p_spu_id=(\d+)/);
  if (selfMatch) return selfMatch[1];
  const topFrame = document.querySelector('frame[name="top"]');
  if (topFrame) { const m = topFrame.src.match(/p4=(\d+)/); if (m) return m[1]; }
  try { const href = getFrame('bottom').location.href; const m = href.match(/p_spu_id=(\d+)/); if (m) return m[1]; } catch(e) {}
  return null;
}

function parseTableToMap(doc) {
  const map = {};
  doc.querySelectorAll('table tr').forEach(row => {
    const cells = row.querySelectorAll('td');
    if (cells.length >= 2) {
      const key = cells[0].innerText.replace(/:$/, '').trim();
      const val = cells[1].innerText.trim();
      if (key) map[key] = val;
    }
  });
  return map;
}

function extractDirectorLinks(doc) {
  const links = [];
  doc.querySelectorAll('a[href*="DIR11.QueryView"]').forEach(a => links.push(a.href));
  return [...new Set(links)];
}

function extractAnnualReturns(doc) {
  const returns = [];
  const arTable = [...doc.querySelectorAll('table')].find(t => {
    const prev = t.closest('p')?.previousElementSibling || t.previousElementSibling;
    return prev?.innerText?.includes('Annual Return');
  });
  if (!arTable) return returns;
  arTable.querySelectorAll('tr').forEach(row => {
    const cells = row.querySelectorAll('td');
    if (cells.length >= 2 && cells[0].innerText.trim() !== 'File Year') {
      returns.push({ year: cells[0].innerText.trim(), filed: cells[1].innerText.trim() });
    }
  });
  return returns;
}

async function navigateBottom(url) {
  return new Promise((resolve, reject) => {
    const noFrameset = document.querySelectorAll('frame').length === 0;
    if (noFrameset) {
      const timeout = setTimeout(() => reject(new Error('navigation timeout: ' + url)), CFG.navTimeoutMs);
      window.addEventListener('load', function onLoad() {
        window.removeEventListener('load', onLoad);
        clearTimeout(timeout);
        setTimeout(() => resolve(window), 800);
      });
      window.location.href = url;
    } else {
      const bottom = getFrame('bottom');
      if (!bottom) return reject(new Error('bottom frame not found'));
      bottom.location.href = url;
      const timeout = setTimeout(() => reject(new Error('navigation timeout: ' + url)), CFG.navTimeoutMs);
      let settled = false;
      const check = setInterval(() => {
        try {
          const f = getFrame('bottom');
          if (f && f.document.readyState === 'complete' && !settled) {
            settled = true; clearInterval(check); clearTimeout(timeout);
            setTimeout(() => resolve(f), 800);
          }
        } catch(e) {}
      }, 300);
    }
  });
}

async function goToSearchForm(spuId) {
  return new Promise((resolve, reject) => {
    const bottom = getFrame('bottom');
    if (!bottom) return reject(new Error('bottom frame not found'));
    bottom.location.href = `${CFG.BASE}/cr3450a$.startup?p_spu_id=${spuId}`;
    const timeout = setTimeout(() => reject(new Error('search form timeout')), CFG.navTimeoutMs);
    const check = setInterval(() => {
      try {
        const f = getFrame('bottom');
        if (f && f.document.readyState === 'complete' && f.document.querySelector('input[name="P_LE_NAME"]')) {
          clearInterval(check); clearTimeout(timeout);
          setTimeout(() => resolve(f), 500);
        }
      } catch(e) {}
    }, 300);
  });
}

// ── SCRAPE ONE COMPANY ───────────────────────────────────────
async function scrapeOneCompany(searchName, knownCAN) {
  const spuId = getSpuId();
  if (!spuId) throw new Error('Could not detect SPU ID — make sure you are logged in to CORES.');

  const searchFrame = await goToSearchForm(spuId);
  searchFrame.document.querySelector('input[name="P_LE_NAME"]').value = searchName;
  searchFrame.document.querySelector('input[name="Z_ACTION"][value="Find"]').click();
  await pause(CFG.afterSearch);

  const resultFrame = getFrame('bottom');
  const corrLink = resultFrame.document.querySelector('a[href*="CorrCheck"]');
  if (!corrLink) throw new Error('NO_MATCH');

  const can = knownCAN || corrLink.innerText.trim();
  const regIdMatch = corrLink.href.match(/p_reg_id=(\d+)/);
  if (!regIdMatch) throw new Error('Could not extract reg_id for: ' + searchName);

  const srUrl = `${CFG.BASE}/cr_search_custom_code.CorrCheck?p_mod=cr3450a&p_ttype=94&p_spu_id=${spuId}&p_reg_id=${regIdMatch[1]}`;
  const srFrame = await navigateBottom(srUrl);
  await pause(CFG.betweenSteps);

  const srLink = srFrame.document.querySelector('a[href*="display_sr"]');
  if (!srLink) throw new Error('No service request found for: ' + searchName);

  const leIdMatch = srLink.href.match(/p_le_id=(\d+)/);
  if (!leIdMatch) throw new Error('Could not extract le_id for: ' + searchName);

  const leUrl = `${CFG.BASE}/CR3450B$LE2.Queryview?P_LEGAL_ENTITY_ID3=${leIdMatch[1]}`;
  const leFrame = await navigateBottom(leUrl);
  await pause(CFG.betweenSteps);

  return await extractAllData(can, searchName, leFrame);
}

async function extractAllData(can, searchName, leFrame) {
  const doc = leFrame.document;
  const companyMap = parseTableToMap(doc);
  const annualReturns = extractAnnualReturns(doc);
  const lastReturn = annualReturns[0] || { year: '', filed: '' };

  const agentTable = [...doc.querySelectorAll('table')].find(t => {
    const prev = t.closest('p')?.previousElementSibling || t.previousElementSibling;
    return prev?.innerText?.includes('Agent for Service');
  });
  let agentName = '';
  if (agentTable) {
    const cells = agentTable.querySelectorAll('td');
    if (cells.length >= 2) agentName = `${cells[0].innerText.trim()} ${cells[1].innerText.trim()}`.trim();
  }

  const company = {
    CAN: can,
    Legal_Name: companyMap['Legal Entity Name'] || searchName,
    Status: companyMap['Legal Entity Status'] || '',
    LE_Type: companyMap['Legal Entity Type'] || '',
    Corp_Type: companyMap['Alberta Corporation Type'] || '',
    Nuans_Number: companyMap['Nuans Number'] || '',
    Nuans_Date: (companyMap['Nuans Date'] || '').replace(/\s*\(YYYY\/MM\/DD\)/i, '').trim(),
    Reg_Street: companyMap['Street/Box Number'] || '',
    Reg_City: companyMap['City'] || '',
    Reg_Province: companyMap['Province'] || '',
    Reg_Postal: companyMap['Postal Code'] || '',
    Email: companyMap['Email Address'] || '',
    Min_Directors: companyMap['Min Number Of Directors'] || '',
    Max_Directors: companyMap['Max Number Of Directors'] || '',
    Registration_Date: (companyMap['Registration Date'] || '').replace(/\s*\(YYYY\/MM\/DD\)/i, '').trim(),
    Agent_For_Service: agentName,
    Last_AR_Year: lastReturn.year,
    Last_AR_Filed: lastReturn.filed,
    All_Annual_Returns: annualReturns.map(r => `${r.year}:${r.filed}`).join('; '),
  };

  const directorLinks = extractDirectorLinks(doc);
  log(`  [${can}] ${company.Legal_Name} — ${directorLinks.length} director(s)`);

  const directors = [];
  for (const href of directorLinks) {
    try {
      const dirFrame = await navigateBottom(href);
      await pause(CFG.betweenDirectors);
      const dirMap = parseTableToMap(dirFrame.document);
      directors.push({
        CAN: can,
        Company_Name: company.Legal_Name,
        Last_Name: dirMap['Last Name / Corporation Name'] || '',
        First_Name: dirMap['First Name'] || '',
        Middle_Name: dirMap['Middle Name'] || '',
        Director_Corp_CAN: dirMap['Corporate Access Number'] || '',
        Status: dirMap['Director Shareholder Status'] || '',
        Type: dirMap['Director Shareholder Type'] || '',
        Individual_or_Corp: dirMap['Individual / Corporation Type'] || '',
        Street: dirMap['Street/Box Number'] || '',
        City: dirMap['City'] || '',
        Province: dirMap['Province'] || '',
        Postal: dirMap['Postal Code'] || '',
        Country: dirMap['Country'] || '',
        Appointment_Date: (dirMap['Appointment Date'] || '').replace(/\s*\(YYYY\/MM\/DD\)/i, '').trim(),
        Cessation_Date: (dirMap['Cessation Date'] || '').replace(/\s*\(YYYY\/MM\/DD\)/i, '').trim(),
        Percent_Voting_Shares: dirMap['Percent Of Voting Shares'] || '',
      });
      log(`    Dir: ${dirMap['Last Name / Corporation Name']}, ${dirMap['First Name']} [${dirMap['Individual / Corporation Type']}]`);
    } catch(e) {
      log(`    WARNING: Could not load director link — ${e.message}`);
    }
  }

  return { company, directors };
}

// ── RETRY WRAPPER ────────────────────────────────────────────
async function scrapeWithRetry(searchName, knownCAN, label) {
  let attempt = 0;
  while (attempt < CFG.maxRetries) {
    try {
      return await scrapeOneCompany(searchName, knownCAN);
    } catch(e) {
      if (e.message === 'NO_MATCH') {
        log(`  [SKIP] No match: "${searchName}"`);
        return { noMatch: true };
      }
      if (e.message.includes('timeout') && attempt < CFG.maxRetries - 1) {
        attempt++;
        const backoff = CFG.backoffBaseMs * Math.pow(2, attempt - 1);
        log(`  [RETRY ${attempt}/${CFG.maxRetries - 1}] Timeout on "${searchName}" — waiting ${backoff / 1000}s`);
        await sleep(backoff);
      } else {
        log(`  [ERROR] "${searchName}": ${e.message}`);
        return { error: e.message };
      }
    }
  }
  return { error: 'Max retries exceeded' };
}

// ── PROGRESS PERSISTENCE ─────────────────────────────────────
function saveProgress(data) {
  try { localStorage.setItem('cores_progress', JSON.stringify(data)); } catch(e) {}
}

function loadProgress() {
  try { const d = localStorage.getItem('cores_progress'); return d ? JSON.parse(d) : null; } catch(e) { return null; }
}

function clearProgress() {
  try { localStorage.removeItem('cores_progress'); } catch(e) {}
}

// ── CSV UTILS ────────────────────────────────────────────────
function toCSV(rows) {
  if (!rows || rows.length === 0) return '';
  const headers = Object.keys(rows[0]);
  const lines = [headers.join(',')];
  rows.forEach(row => {
    lines.push(headers.map(h => `"${(row[h] || '').toString().replace(/"/g, '""')}"`).join(','));
  });
  return lines.join('\n');
}

function downloadCSV(content, filename) {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

function parseCSV(text) {
  const lines = text.trim().split('\n');
  const headers = lines[0].split(',').map(h => h.replace(/^"|"$/g, '').trim());
  return lines.slice(1).map(line => {
    const vals = []; let cur = '', inQ = false;
    for (let i = 0; i < line.length; i++) {
      const c = line[i];
      if (c === '"') { inQ = !inQ; }
      else if (c === ',' && !inQ) { vals.push(cur); cur = ''; }
      else cur += c;
    }
    vals.push(cur);
    const obj = {};
    headers.forEach((h, i) => { obj[h] = (vals[i] || '').replace(/^"|"$/g, '').trim(); });
    return obj;
  });
}

async function parseXLSX(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = e => {
      try {
        const data = new Uint8Array(e.target.result);
        const workbook = XLSX.read(data, { type: 'array' });
        const sheet = workbook.Sheets[workbook.SheetNames[0]];
        const rows = XLSX.utils.sheet_to_json(sheet, { header: 1 });
        const headers = rows[0].map(h => String(h).trim());
        const result = rows.slice(1).map(row => {
          const obj = {};
          headers.forEach((h, i) => { obj[h] = row[i] != null ? String(row[i]).trim() : ''; });
          return obj;
        }).filter(r => Object.values(r).some(v => v));
        resolve(result);
      } catch(err) { reject(err); }
    };
    reader.onerror = () => reject(new Error('File read error'));
    reader.readAsArrayBuffer(file);
  });
}

async function loadXLSXLib() {
  if (window.XLSX) return;
  await new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js';
    s.onload = resolve; s.onerror = () => reject(new Error('Failed to load XLSX library'));
    document.head.appendChild(s);
  });
}

// ── PHASE 1 ──────────────────────────────────────────────────
async function runPhase1(names, resumeFrom) {
  const failed = [], noMatch = [];
  const startIdx = resumeFrom || 0;
  const total = names.length;

  log(`\n======= PHASE 1 — ${total} companies (starting at #${startIdx + 1}) =======`);

  for (let i = startIdx; i < total; i++) {
    const name = names[i];
    updateStatus(`Phase 1 | [${i + 1}/${total}] ${name} | Co: ${p1Companies.length} | Dir: ${p1Directors.length}`);
    log(`\n[${i + 1}/${total}] ${name}`);

    const result = await scrapeWithRetry(name, null, `P1 #${i + 1}`);

    if (result.noMatch) noMatch.push({ name, reason: 'No match in CORES' });
    else if (result.error) failed.push({ name, reason: result.error });
    else {
      p1Companies.push(result.company);
      p1Directors.push(...result.directors);
    }

    saveProgress({ phase: 1, index: i + 1, names, p1Companies, p1Directors });

    // Long pause every N companies
    if ((i + 1) % CFG.longPauseEveryN === 0 && i < total - 1) {
      const pauseMs = overnightMode ? CFG.longPauseMsOvernight : CFG.longPauseMs;
      log(`\n[LONG PAUSE] ${pauseMs / 1000}s after ${i + 1} companies...`);
      updateStatus(`Pausing ${pauseMs / 1000}s (anti-block)...`);
      await sleep(pauseMs);
    } else {
      await pause(CFG.betweenCompanies);
    }
  }

  // Download Phase 1 CSVs
  const ts = new Date().toISOString().slice(0, 16).replace(/[:T]/g, '').replace(/-/g, '');
  const tsFormatted = `${ts.slice(0,8)}${ts.slice(8)}`;
  const tsLabel = new Date().toISOString().slice(0,16).replace('T','').replace(/:/g,'').replace(/-/g,'');

  if (p1Companies.length > 0) {
    downloadCSV(toCSV(p1Companies), `cores_companies_${tsLabel}.csv`);
    await sleep(600);
    downloadCSV(toCSV(p1Directors), `cores_directors_${tsLabel}.csv`);
    await sleep(600);
  }
  if (failed.length > 0 || noMatch.length > 0) {
    const errRows = [...noMatch.map(n => ({ name: n.name, reason: n.reason })), ...failed.map(f => ({ name: f.name, reason: f.reason }))];
    downloadCSV(toCSV(errRows), `cores_errors_${tsLabel}.csv`);
  }

  log(`\n===== PHASE 1 DONE: ${p1Companies.length} companies, ${p1Directors.length} directors =====`);
  updateStatus(`Phase 1 done! ${p1Companies.length} co, ${p1Directors.length} dir — CSVs downloaded`);

  return tsLabel;
}

// ── PHASE 2 ──────────────────────────────────────────────────
async function runPhase2(tsLabel) {
  const visitedCANs = new Set();
  const failed = [];
  const queue = [];
  const queued = new Set();

  // Mark all Phase 1 company CANs as visited
  p1Companies.forEach(c => { if (c.CAN) visitedCANs.add(String(c.CAN).trim()); });

  // Build initial queue from Phase 1 directors
  p1Directors.forEach(r => {
    if (r.Individual_or_Corp === 'Legal Entity' && r.Director_Corp_CAN && r.Director_Corp_CAN.trim()) {
      const subCAN = r.Director_Corp_CAN.trim();
      if (!queued.has(subCAN) && !visitedCANs.has(subCAN)) {
        queue.push({ can: subCAN, companyName: r.Last_Name, parentCAN: r.CAN, parentName: r.Company_Name, depth: 2 });
        queued.add(subCAN);
      }
    }
  });

  // Flag un-traceable "Other" entries
  const noCANCorps = p1Directors.filter(r =>
    r.Individual_or_Corp === 'Other' &&
    /\b(LTD|INC|CORP|HOLDINGS|TRUST|ENTERPRISES|PROPERTIES|INVESTMENTS|MANAGEMENT)\b/i.test(r.Last_Name)
  );
  if (noCANCorps.length) {
    log(`\nNOTE: ${noCANCorps.length} "Other" shareholders look like companies but have no CAN — cannot trace:`);
    noCANCorps.forEach(r => log(`  - ${r.Last_Name} (of ${r.Company_Name})`));
  }

  log(`\n======= PHASE 2 — ${queue.length} corporate shareholders queued =======`);

  let processed = 0;

  while (queue.length > 0) {
    const { can, companyName, parentCAN, parentName, depth } = queue.shift();
    if (visitedCANs.has(can)) continue;
    visitedCANs.add(can);
    processed++;

    updateStatus(`Phase 2 | Depth ${depth} | Queue: ${queue.length} | Co: ${p2Companies.length} | Dir: ${p2Directors.length}`);
    log(`\n[Depth ${depth}] "${companyName}" CAN: ${can} (child of: ${parentName})`);

    const result = await scrapeWithRetry(companyName, can, `P2 depth${depth}`);

    if (result.noMatch) {
      failed.push({ can, companyName, parentCAN, reason: 'No match in CORES' });
    } else if (result.error) {
      failed.push({ can, companyName, parentCAN, reason: result.error });
    } else {
      result.company.depth = depth;
      result.company.parent_CAN = parentCAN;
      result.directors.forEach(d => { d.depth = depth; d.parent_CAN = parentCAN; });

      p2Companies.push(result.company);
      p2Directors.push(...result.directors);

      // Discover next-level corporate shareholders
      result.directors.forEach(d => {
        if (d.Individual_or_Corp === 'Legal Entity' && d.Director_Corp_CAN && d.Director_Corp_CAN.trim()) {
          const subCAN = d.Director_Corp_CAN.trim();
          if (!queued.has(subCAN) && !visitedCANs.has(subCAN)) {
            queue.push({ can: subCAN, companyName: d.Last_Name, parentCAN: can, parentName: result.company.Legal_Name, depth: depth + 1 });
            queued.add(subCAN);
            log(`  Queued sub-company: ${d.Last_Name} (CAN: ${subCAN}) at depth ${depth + 1}`);
          }
        }
      });
    }

    saveProgress({ phase: 2, p1Companies, p1Directors, p2Companies, p2Directors, queue, visitedCANs: [...visitedCANs] });

    if (processed % CFG.longPauseEveryN === 0 && queue.length > 0) {
      const pauseMs = overnightMode ? CFG.longPauseMsOvernight : CFG.longPauseMs;
      log(`\n[LONG PAUSE] ${pauseMs / 1000}s after ${processed} Phase 2 companies...`);
      updateStatus(`Pausing ${pauseMs / 1000}s (anti-block)...`);
      await sleep(pauseMs);
    } else {
      await pause(CFG.betweenCompanies);
    }
  }

  // Download Phase 2 CSVs
  if (p2Companies.length > 0) {
    downloadCSV(toCSV(p2Companies), `cores_companies_deep_${tsLabel}.csv`);
    await sleep(600);
    downloadCSV(toCSV(p2Directors), `cores_directors_deep_${tsLabel}.csv`);
    await sleep(600);
  }
  if (failed.length > 0) {
    downloadCSV(toCSV(failed), `cores_errors_deep_${tsLabel}.csv`);
  }

  clearProgress();

  log(`\n===== PHASE 2 DONE: ${p2Companies.length} companies, ${p2Directors.length} directors =====`);
  updateStatus(`ALL DONE! P1: ${p1Companies.length} co / ${p1Directors.length} dir — P2: ${p2Companies.length} co / ${p2Directors.length} dir`);
}

// ── UI ───────────────────────────────────────────────────────
let logBox, statusEl;

function log(msg) {
  if (logBox) { logBox.value += msg + '\n'; logBox.scrollTop = logBox.scrollHeight; }
  console.log('[CORES]', msg);
}

function updateStatus(msg) {
  if (statusEl) statusEl.innerText = msg;
}

function showConfirmPhase2(tsLabel) {
  return new Promise(resolve => {
    const target = getFrame('bottom') ? getFrame('bottom').document.body : document.body;
    const modal = document.createElement('div');
    modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.65);z-index:999999;display:flex;align-items:center;justify-content:center';
    modal.innerHTML = `
      <div style="background:#1e1e2e;color:#cdd6f4;font-family:monospace;padding:28px;border-radius:12px;max-width:420px;width:90%;box-shadow:0 6px 32px rgba(0,0,0,0.7);border:1px solid #45475a">
        <div style="font-size:15px;font-weight:bold;color:#89b4fa;margin-bottom:10px">Phase 1 Complete</div>
        <div style="margin-bottom:16px;font-size:13px;line-height:1.6">
          Found <strong style="color:#a6e3a1">${p2Companies.length || '...'}</strong> corporate shareholders queued for Phase 2.<br>
          Ready to run the deep scrape?
        </div>
        <div style="display:flex;gap:10px">
          <button id="p2-yes" style="flex:1;background:#a6e3a1;color:#1e1e2e;border:none;padding:9px;border-radius:6px;cursor:pointer;font-weight:bold;font-size:13px">Yes, run Phase 2</button>
          <button id="p2-no" style="flex:1;background:#45475a;color:#cdd6f4;border:none;padding:9px;border-radius:6px;cursor:pointer;font-size:13px">No, stop here</button>
        </div>
      </div>`;
    target.appendChild(modal);
    modal.querySelector('#p2-yes').onclick = () => { modal.remove(); resolve(true); };
    modal.querySelector('#p2-no').onclick = () => { modal.remove(); resolve(false); };
  });
}

function showUI() {
  const target = getFrame('bottom') ? getFrame('bottom').document.body : document.body;
  const existing = target.querySelector('#cores-ui') || document.getElementById('cores-ui');
  if (existing) existing.remove();

  const panel = document.createElement('div');
  panel.id = 'cores-ui';
  panel.style.cssText = 'position:fixed;top:20px;right:20px;z-index:99999;background:#1e1e2e;color:#cdd6f4;font-family:monospace;font-size:13px;padding:20px;border-radius:10px;width:400px;box-shadow:0 4px 24px rgba(0,0,0,0.5);border:1px solid #45475a;max-height:90vh;overflow-y:auto';

  panel.innerHTML = `
    <div style="font-size:15px;font-weight:bold;margin-bottom:4px;color:#89b4fa">CORES Unified Scraper</div>
    <div style="font-size:11px;color:#6c7086;margin-bottom:14px">Phase 1 + Phase 2 — Paste in TOP frame context</div>

    <label style="color:#a6e3a1;font-size:12px">Upload company list (CSV or XLSX — first column = company names)</label>
    <input type="file" id="c-file" accept=".csv,.xlsx"
      style="width:100%;background:#313244;color:#cdd6f4;border:1px solid #45475a;border-radius:5px;padding:5px;font-size:12px;box-sizing:border-box;margin:6px 0 10px">

    <div style="margin-bottom:12px">
      <label style="color:#f9e2af;font-size:12px">Mode</label>
      <div style="display:flex;gap:8px;margin-top:5px">
        <button id="c-mode-normal" style="flex:1;background:#89b4fa;color:#1e1e2e;border:none;padding:7px;border-radius:5px;cursor:pointer;font-weight:bold;font-size:12px">Normal</button>
        <button id="c-mode-overnight" style="flex:1;background:#313244;color:#cdd6f4;border:1px solid #45475a;padding:7px;border-radius:5px;cursor:pointer;font-size:12px">Overnight 🌙</button>
      </div>
      <div id="c-mode-desc" style="font-size:11px;color:#6c7086;margin-top:5px">Normal: asks before Phase 2, standard delays.</div>
    </div>

    <div style="margin-bottom:12px">
      <label style="color:#f9e2af;font-size:12px">Start Phase</label>
      <div style="display:flex;gap:8px;margin-top:5px">
        <button id="c-p1" style="flex:1;background:#a6e3a1;color:#1e1e2e;border:none;padding:7px;border-radius:5px;cursor:pointer;font-weight:bold;font-size:12px">Phase 1</button>
        <button id="c-p2only" style="flex:1;background:#313244;color:#cdd6f4;border:1px solid #45475a;padding:7px;border-radius:5px;cursor:pointer;font-size:12px">Phase 2 Only</button>
      </div>
      <div style="font-size:11px;color:#6c7086;margin-top:3px">"Phase 2 Only" expects Phase 1 directors CSV as input.</div>
    </div>

    <div id="c-resume-banner" style="display:none;background:#313244;border:1px solid #f9e2af;border-radius:5px;padding:8px;margin-bottom:10px;font-size:12px;color:#f9e2af">
      ⚡ Saved progress found! <button id="c-resume" style="background:#f9e2af;color:#1e1e2e;border:none;padding:3px 8px;border-radius:4px;cursor:pointer;font-size:11px;margin-left:6px">Resume</button>
      <button id="c-discard" style="background:#45475a;color:#cdd6f4;border:none;padding:3px 8px;border-radius:4px;cursor:pointer;font-size:11px;margin-left:4px">Discard</button>
    </div>

    <div id="c-status" style="padding:7px;background:#313244;border-radius:5px;min-height:28px;font-size:12px;color:#f9e2af;margin-bottom:8px;word-break:break-word">
      Upload a file and select a mode.
    </div>
    <textarea id="c-log" readonly
      style="width:100%;height:180px;background:#181825;color:#a6e3a1;border:1px solid #313244;border-radius:5px;padding:6px;font-family:monospace;font-size:11px;resize:none;box-sizing:border-box;margin-bottom:8px"></textarea>
    <button id="c-close" style="width:100%;background:#45475a;color:#cdd6f4;border:none;padding:5px;border-radius:5px;cursor:pointer;font-size:11px">Close</button>
  `;

  target.appendChild(panel);
  logBox = target.querySelector('#c-log');
  statusEl = target.querySelector('#c-status');

  // Mode toggle
  let selectedMode = 'normal';
  const modeDesc = target.querySelector('#c-mode-desc');
  target.querySelector('#c-mode-normal').onclick = () => {
    selectedMode = 'normal';
    overnightMode = false;
    target.querySelector('#c-mode-normal').style.background = '#89b4fa';
    target.querySelector('#c-mode-normal').style.color = '#1e1e2e';
    target.querySelector('#c-mode-overnight').style.background = '#313244';
    target.querySelector('#c-mode-overnight').style.color = '#cdd6f4';
    modeDesc.innerText = 'Normal: asks before Phase 2, standard delays.';
  };
  target.querySelector('#c-mode-overnight').onclick = () => {
    selectedMode = 'overnight';
    overnightMode = true;
    target.querySelector('#c-mode-overnight').style.background = '#cba6f7';
    target.querySelector('#c-mode-overnight').style.color = '#1e1e2e';
    target.querySelector('#c-mode-normal').style.background = '#313244';
    target.querySelector('#c-mode-normal').style.color = '#cdd6f4';
    modeDesc.innerText = '🌙 Overnight: Phase 1 → Phase 2 automatic, 2× delays, longer pauses.';
  };

  // Resume banner
  const saved = loadProgress();
  if (saved) {
    target.querySelector('#c-resume-banner').style.display = 'block';
    target.querySelector('#c-resume').onclick = async () => {
      target.querySelector('#c-resume-banner').style.display = 'none';
      p1Companies = saved.p1Companies || [];
      p1Directors = saved.p1Directors || [];
      p2Companies = saved.p2Companies || [];
      p2Directors = saved.p2Directors || [];
      log(`Resumed: ${p1Companies.length} P1 co, ${p1Directors.length} P1 dir loaded from saved progress.`);
      if (saved.phase === 1) {
        const remaining = saved.names.slice(saved.index);
        log(`Resuming Phase 1 from index ${saved.index} (${remaining.length} remaining)...`);
        const tsLabel = await runPhase1(saved.names, saved.index);
        if (overnightMode || await showConfirmPhase2(tsLabel)) {
          await runPhase2(tsLabel);
        }
      } else if (saved.phase === 2) {
        log(`Resuming Phase 2 from saved queue...`);
        const fakeTs = new Date().toISOString().slice(0, 16).replace(/[:T-]/g, '');
        await runPhase2(fakeTs);
      }
    };
    target.querySelector('#c-discard').onclick = () => {
      clearProgress();
      target.querySelector('#c-resume-banner').style.display = 'none';
      log('Saved progress discarded.');
    };
  }

  target.querySelector('#c-close').onclick = () => panel.remove();

  // Phase 1
  target.querySelector('#c-p1').onclick = async () => {
    const fileInput = target.querySelector('#c-file');
    if (!fileInput.files[0]) { updateStatus('Upload a CSV or XLSX file first.'); return; }

    try {
      let rows;
      const file = fileInput.files[0];
      if (file.name.endsWith('.xlsx')) {
        await loadXLSXLib();
        rows = await parseXLSX(file);
      } else {
        rows = parseCSV(await file.text());
      }

      // Extract company names from first non-header column
      const firstKey = Object.keys(rows[0])[0];
      const skipHeaders = ['company','name','legal name','company name','legal_name'];
      const names = rows
        .map(r => (r[firstKey] || Object.values(r)[0] || '').trim())
        .filter(n => n && !skipHeaders.includes(n.toLowerCase()));

      if (!names.length) { updateStatus('No valid company names found.'); return; }
      log(`Loaded ${names.length} companies from ${file.name}`);

      setRunning(target, true);
      const tsLabel = await runPhase1(names, 0);

      if (overnightMode) {
        await runPhase2(tsLabel);
      } else {
        const go = await showConfirmPhase2(tsLabel);
        if (go) await runPhase2(tsLabel);
        else log('Stopped after Phase 1 by user choice.');
      }
      setRunning(target, false);
    } catch(e) {
      updateStatus('Error: ' + e.message);
      log('ERROR: ' + e.message);
      setRunning(target, false);
    }
  };

  // Phase 2 only (upload Phase 1 directors CSV)
  target.querySelector('#c-p2only').onclick = async () => {
    const fileInput = target.querySelector('#c-file');
    if (!fileInput.files[0]) { updateStatus('Upload Phase 1 directors CSV first.'); return; }
    try {
      const file = fileInput.files[0];
      let rows;
      if (file.name.endsWith('.xlsx')) {
        await loadXLSXLib();
        rows = await parseXLSX(file);
      } else {
        rows = parseCSV(await file.text());
      }
      p1Directors = rows;
      // Extract companies to populate p1Companies for visited tracking
      const uniqueCANs = [...new Set(rows.map(r => r.CAN).filter(Boolean))];
      p1Companies = uniqueCANs.map(can => ({ CAN: can }));
      log(`Loaded ${rows.length} director rows. Running Phase 2 only...`);
      setRunning(target, true);
      const tsLabel = new Date().toISOString().slice(0, 16).replace(/[:T-]/g, '');
      await runPhase2(tsLabel);
      setRunning(target, false);
    } catch(e) {
      updateStatus('Error: ' + e.message);
      log('ERROR: ' + e.message);
      setRunning(target, false);
    }
  };

  log('Panel ready. Upload your company list and choose a mode.');
  log('IMPORTANT: Make sure you are in the TOP frame context in DevTools.');
}

function setRunning(target, running) {
  target.querySelector('#c-p1').disabled = running;
  target.querySelector('#c-p2only').disabled = running;
  target.querySelector('#c-p1').style.opacity = running ? '0.5' : '1';
  target.querySelector('#c-p2only').style.opacity = running ? '0.5' : '1';
}

showUI();

})();
