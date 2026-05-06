# @title 4 — ASSEMBLE FINAL HTML
# Inputs: mindmap_section.html, dashboard_section.html
# Output: cores_gettel_explorer.html

import re, os

with open("mindmap_section.html","r",encoding="utf-8") as f:
    mm = f.read()

with open("dashboard_section.html","r",encoding="utf-8") as f:
    db = f.read()

def extract_blocks(html, tag):
    pattern = rf'<{tag}[^>]*>(.*?)</{tag}>'
    return re.findall(pattern, html, re.DOTALL)

def strip_blocks(html, tag):
    pattern = rf'<{tag}[^>]*>.*?</{tag}>'
    return re.sub(pattern, '', html, flags=re.DOTALL).strip()

mm_styles  = extract_blocks(mm, 'style')
db_styles  = extract_blocks(db, 'style')
mm_scripts = extract_blocks(mm, 'script')
db_scripts = extract_blocks(db, 'script')
mm_body    = strip_blocks(strip_blocks(mm, 'style'), 'script').strip()
db_body    = strip_blocks(strip_blocks(db, 'style'), 'script').strip()

# Deduplicate the Google Fonts import (both sections share it)
FONT_IMPORT = "@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');"
all_styles = '\n'.join(mm_styles + db_styles)
all_styles = all_styles.replace(FONT_IMPORT, '', 1)  # keep only one

final = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CORES + GETTEL Explorer</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    {FONT_IMPORT}
    *{{box-sizing:border-box;margin:0;padding:0;}}
    body{{font-family:'DM Sans',sans-serif;background:#f8f8f6;color:#1a1a1a;height:100vh;overflow:hidden;}}
    .top-nav{{display:flex;align-items:center;gap:0;background:#111;padding:0 20px;height:42px;}}
    .top-nav .nav-brand{{color:#fff;font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;margin-right:20px;}}
    .nav-tab{{padding:0 18px;height:42px;font-family:inherit;font-size:12px;font-weight:500;color:rgba(255,255,255,.6);background:none;border:none;border-bottom:2px solid transparent;cursor:pointer;letter-spacing:.02em;}}
    .nav-tab.active{{color:#fff;border-bottom-color:#fff;}}
    .nav-tab:hover{{color:#fff;}}
    .tab-content{{display:none;height:calc(100vh - 42px);overflow:hidden;}}
    .tab-content.active{{display:block;}}
    {all_styles}
  </style>
</head>
<body>

  <nav class="top-nav">
    <span class="nav-brand">CORES + GETTEL</span>
    <button class="nav-tab active" data-tab="mindmap"   onclick="switchTab('mindmap')">Network Map</button>
    <button class="nav-tab"        data-tab="dashboard" onclick="switchTab('dashboard')">Dashboard</button>
  </nav>

  <div id="tab-mindmap"   class="tab-content active">
    {mm_body}
  </div>
  <div id="tab-dashboard" class="tab-content">
    {db_body}
  </div>

  <script>
    var _mmInited = false;
    var _dbInited = false;

    function switchTab(tab) {{
      document.querySelectorAll('.nav-tab').forEach(b=>b.classList.toggle('active', b.dataset.tab===tab));
      document.querySelectorAll('.tab-content').forEach(c=>c.classList.remove('active'));
      document.getElementById('tab-'+tab).classList.add('active');
      if(tab==='mindmap' && !_mmInited) {{ _mmInited=true; initMindmap(); }}
      if(tab==='dashboard' && !_dbInited) {{ _dbInited=true; initDashboard(); }}
    }}

    // Mindmap init (deferred until tab shown)
    function initMindmap() {{
      {chr(10).join(mm_scripts)}
    }}

    // Dashboard init (deferred until tab shown)
    function initDashboard() {{
      {chr(10).join(db_scripts)}
    }}

    // Auto-init mindmap on first load
    _mmInited = true;
    initMindmap();
  </script>

</body>
</html>"""

with open("cores_gettel_explorer.html","w",encoding="utf-8") as f:
    f.write(final)

size_mb = os.path.getsize("cores_gettel_explorer.html") / 1024 / 1024
print(f"cores_gettel_explorer.html written.")
print(f"  Total size: {size_mb:.2f} MB")
print(f"  (Data size scales with your input — this measures the HTML+JS template only)")
