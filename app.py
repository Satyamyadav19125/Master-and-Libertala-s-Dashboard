import os, re
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Digital Village · Farm Intelligence", layout="wide", page_icon="🌾")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #0f1117; }
[data-testid="stSidebar"] { background: #161b22 !important; border-right: 1px solid #21262d; }
section.main > div { padding-top: 1rem; }
.proj-header { background:linear-gradient(135deg,#0d2137 0%,#0a3d1f 100%); border-radius:14px; padding:22px 28px; margin-bottom:18px; border:1px solid #1e4d2b; }
.proj-header h1 { margin:0; font-size:1.6rem; color:#fff; font-weight:800; }
.proj-header .sub { color:#7ec8a0; font-size:0.88rem; margin-top:4px; }
.proj-header .credits { color:#a0c4b0; font-size:0.8rem; margin-top:10px; }
.stat-row { display:flex; gap:10px; flex-wrap:wrap; margin-bottom:16px; }
.stat-chip { background:#161b22; border:1px solid #30363d; border-radius:10px; padding:10px 16px; flex:1; min-width:90px; text-align:center; }
.stat-chip .num { font-size:1.5rem; font-weight:800; color:#58a6ff; }
.stat-chip .lbl { font-size:0.72rem; color:#8b949e; text-transform:uppercase; letter-spacing:.5px; margin-top:2px; }
.farm-header { background:linear-gradient(135deg,#1a3a1a,#1e4620); border:1px solid #2ea043; border-radius:12px; padding:16px 20px; margin-bottom:14px; }
.farm-header .fid { font-size:0.75rem; color:#7ec8a0; letter-spacing:1px; text-transform:uppercase; }
.farm-header h2 { margin:3px 0; font-size:1.25rem; color:#fff; font-weight:700; }
.farm-header .meta { color:#a0c4b0; font-size:0.85rem; margin-top:4px; }
.card { background:#161b22; border:1px solid #21262d; border-radius:10px; padding:14px 16px; margin-bottom:10px; }
.card .card-title { font-size:0.72rem; color:#8b949e; text-transform:uppercase; letter-spacing:.8px; font-weight:600; margin-bottom:10px; padding-bottom:6px; border-bottom:1px solid #21262d; }
.kv { display:flex; justify-content:space-between; padding:5px 0; border-bottom:1px solid #0d1117; align-items:center; }
.kv:last-child { border-bottom:none; }
.kv .k { color:#8b949e; font-size:0.84rem; flex-shrink:0; }
.kv .val { color:#e6edf3; font-size:0.84rem; font-weight:500; text-align:right; margin-left:12px; word-break:break-word; }
.badge-y { background:#1a3a1a; color:#3fb950; border:1px solid #2ea043; padding:2px 8px; border-radius:20px; font-size:0.75rem; font-weight:600; }
.badge-n { background:#3a1a1a; color:#f85149; border:1px solid #b22222; padding:2px 8px; border-radius:20px; font-size:0.75rem; font-weight:600; }
.badge-na { background:#21262d; color:#8b949e; padding:2px 8px; border-radius:20px; font-size:0.75rem; }
.dev-card { background:#0d1117; border:1px solid #30363d; border-radius:8px; padding:10px 14px; margin:6px 0; }
.dev-title { color:#58a6ff; font-size:0.82rem; font-weight:700; margin-bottom:6px; }
.dkv { display:flex; gap:8px; align-items:flex-start; font-size:0.8rem; margin:3px 0; }
.dkv .dk { color:#8b949e; min-width:60px; flex-shrink:0; }
.dkv .dv { color:#e6edf3; word-break:break-all; }
.dkv code { background:#21262d; color:#79c0ff; padding:1px 6px; border-radius:4px; font-size:0.78rem; word-break:break-all; }
.sec { font-size:0.78rem; color:#7ec8a0; text-transform:uppercase; letter-spacing:1px; font-weight:700; margin:14px 0 6px; display:flex; align-items:center; gap:6px; }
.sec::after { content:''; flex:1; height:1px; background:#21262d; }
.sb-proj { background:linear-gradient(135deg,#0d2137,#0a3d1f); border-radius:10px; padding:12px 14px; margin-bottom:12px; border:1px solid #1e4d2b; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300, show_spinner="🌾 Loading farm data from Google Sheets…")
def load_data():
    import requests
    from io import StringIO

    def fetch_sheet(sheet_id, sheet_name):
        # Try gviz first, then export as fallback
        urls = [
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={requests.utils.quote(sheet_name)}",
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&sheet={requests.utils.quote(sheet_name)}",
        ]
        headers = {"User-Agent": "Mozilla/5.0"}
        for url in urls:
            try:
                r = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
                if r.status_code == 200 and len(r.text) > 100:
                    return pd.read_csv(StringIO(r.text), dtype=str, keep_default_na=False)
            except Exception:
                continue
        raise Exception(f"Could not fetch sheet '{sheet_name}' from {sheet_id}")

    # ── Farm Master — "Farm details" sheet ───────────────────────────────────
    df_full = fetch_sheet("10_bnGF7WBZ0J3aSvl8riufNbZjXAxB7wcnN3545fGzw", "Farm details")
    df_full.columns = [str(c).strip() for c in df_full.columns]
    df_k = df_full.iloc[:, 65:121].copy()
    df_k.columns = [str(c).strip() for c in df_k.columns]
    df_k.rename(columns={'Kharif 25 Farm ID': 'Farm ID'}, inplace=True)
    df_k['Farm ID'] = df_k['Farm ID'].str.strip()
    df_k = df_k[df_k['Farm ID'].notna() & (df_k['Farm ID'] != '')]

    # ── Libertalia — "master_control" sheet ──────────────────────────────────
    df_lib = fetch_sheet("14ah-7Ah690oeOXE5vT8p701LYv7PiEMx_xZycNOOrSA", "master_control")
    df_lib.columns = [str(c).strip() for c in df_lib.columns]
    df_lib = df_lib[['Plot code', 'polygons', 'tw location']].copy()
    df_lib.rename(columns={'Plot code': 'Farm ID'}, inplace=True)
    df_lib['Farm ID'] = df_lib['Farm ID'].str.strip()

    df = pd.merge(df_k, df_lib, on='Farm ID', how='inner')
    return df

df = load_data()


# ── Helpers ───────────────────────────────────────────────────────────────────
def v(row, col):
    x = str(row.get(col, '')).strip()
    return '' if x in ('nan', 'None', 'NaN', '') else x

def clean_date(s):
    if not s: return ''
    s = re.sub(r'\s+00:00:00.*', '', s).strip()
    s = re.sub(r'(\d{4})-(\d{2})-(\d{2})', lambda m: f"{m.group(3)}/{m.group(2)}/{m.group(1)}", s)
    return s

def parse_polygon(raw):
    coords = []
    for seg in raw.strip().split(';'):
        p = seg.strip().split()
        if len(p) >= 2:
            try: coords.append((float(p[0]), float(p[1])))
            except: pass
    return coords

def parse_decimal(raw):
    p = raw.strip().split(';')[0].split()
    if len(p) >= 2:
        try: return float(p[0]), float(p[1])
        except: pass
    return None

def parse_dms(s):
    s2 = s.replace('\xb0', '°').replace('\u2019', "'").replace('\u201d', '"').replace('\u2033', '"')
    m = re.findall(r"(\d+)°(\d+)'([\d.]+)\"?([NSEW])", s2)
    if len(m) >= 2:
        def dd(d, mn, sc, di):
            val = float(d) + float(mn)/60 + float(sc)/3600
            return -val if di in ('S','W') else val
        return dd(*m[0]), dd(*m[1])
    return None

def parse_any(raw):
    if not raw or str(raw).strip() in ('nan', 'None', ''): return None
    pt = parse_decimal(raw)
    if pt: return pt
    return parse_dms(raw)

def badge(val):
    u = str(val).strip().upper()
    if u in ('Y','YES','1'): return '<span class="badge-y">✓ Yes</span>'
    if u in ('N','NO','0'):  return '<span class="badge-n">✗ No</span>'
    return f'<span class="badge-na">{val}</span>' if val not in ('','nan','None') else '<span class="badge-na">—</span>'

def kv_row(key, val_html):
    return f'<div class="kv"><span class="k">{key}</span><span class="val">{val_html}</span></div>'

def dkv_row(key, content, code=False):
    inner = f'<code>{content}</code>' if code else content
    return f'<div class="dkv"><span class="dk">{key}</span><span class="dv">{inner}</span></div>'

def has_active_meter(row): return any(v(row,f'Kharif 25 Meter active / {i} (Y/N)').upper() in('Y','YES','1') for i in[1,2])
def has_meter(row):        return any(v(row,f'Kharif 25 Meter serial number / {i}') for i in[1,2])
# #3: pipe counts only if location exists (farms without location go to "no pipe")
def has_pipe(row):         return any(v(row,f'Kharif 25 PVC Pipe location / {i}') for i in[1,2,3,4,5])


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sb-proj">
      <div style="font-size:0.88rem;color:#fff;font-weight:700">🌍 Digital Village Project</div>
      <div style="font-size:0.76rem;color:#7ec8a0;margin-top:3px">Tel Aviv University · Thapar University, Patiala</div>
      <div style="font-size:0.74rem;color:#8b949e;margin-top:8px;line-height:1.5">
        <b style="color:#c9d1d9">Research Lead:</b> Dan Uriel Etgar<br>
        <b style="color:#c9d1d9">Dashboard:</b> Satyam Yadav<br>
        <span style="opacity:.7">Lead Research Assistant</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # #5: Small refresh button in sidebar header area
    col_r1, col_r2 = st.columns([3,1])
    with col_r2:
        if st.button("🔄", help="Reload data from Google Sheets", key="reload_btn"):
            st.cache_data.clear()
            st.rerun()

    # ── #1: Search & Select FIRST ─────────────────────────────────────────────
    st.markdown("#### 🔍 Find a Farm")
    search = st.text_input("Search farm", placeholder="ID, number, name, village…", label_visibility="collapsed")

    st.markdown("---")
    # ── Filter BELOW search ───────────────────────────────────────────────────
    st.markdown("#### ⚙️ Filter by Equipment")
    filter_opt = st.radio("Filter options", [
        "🌾 All farms","💧 Has water meter","🚫 No water meter",
        "✅ Active meter","⛔ Inactive meter","🔧 Has PVC pipes","🪣 No PVC pipes",
    ], label_visibility="collapsed")

    # Build pool from filter
    all_records_list = df.to_dict('records')
    fmap = {
        "💧 Has water meter":  lambda r: has_meter(r),
        "🚫 No water meter":   lambda r: not has_meter(r),
        "✅ Active meter":     lambda r: has_active_meter(r),
        "⛔ Inactive meter":   lambda r: has_meter(r) and not has_active_meter(r),
        "🔧 Has PVC pipes":    lambda r: has_pipe(r),
        "🪣 No PVC pipes":     lambda r: not has_pipe(r),
    }
    pool = [r for r in all_records_list if fmap[filter_opt](r)] if filter_opt in fmap else all_records_list
    pool_ids = sorted(set(r['Farm ID'] for r in pool))

    # Apply search on top of filter
    if search:
        q = search.strip().upper()
        id_m   = [i for i in pool_ids if q in i.upper()]
        name_m = [r['Farm ID'] for r in pool if q in str(r.get('Kharif 25 Farmer Name','')).upper()]
        vil_m  = [r['Farm ID'] for r in pool if q in str(r.get('Kharif 25 Village','')).upper()]
        filtered_ids = sorted(set(id_m + name_m + vil_m))
    else:
        filtered_ids = pool_ids

    st.caption(f"**{len(filtered_ids)}** farms")

    if not filtered_ids:
        st.warning("No farms match."); st.stop()

    selected_id = st.selectbox("Select farm", filtered_ids, index=0, label_visibility="collapsed")


if not selected_id:
    st.info("No farms found."); st.stop()

row = df[df['Farm ID'] == selected_id].iloc[0].to_dict()

farmer_name  = v(row, 'Kharif 25 Farmer Name')
farmer_phone = v(row, 'Kharif 25 Farmer Phone Number')
village      = v(row, 'Kharif 25 Village')
block        = v(row, 'Kharif 25 Block')

# ── Stats — chips reflect current filter (#2) ─────────────────────────────────
all_records = df.to_dict('records')
total_farms = len(df)

# Pre-compute all counts once
c_all        = len(all_records)
c_villages   = df['Kharif 25 Village'].nunique()
c_blocks     = df['Kharif 25 Block'].nunique()
c_meter      = sum(1 for r in all_records if has_meter(r))
c_no_meter   = sum(1 for r in all_records if not has_meter(r))
c_active     = sum(1 for r in all_records if has_active_meter(r))
c_inactive   = sum(1 for r in all_records if has_meter(r) and not has_active_meter(r))
c_pipe       = sum(1 for r in all_records if has_pipe(r))
c_no_pipe    = sum(1 for r in all_records if not has_pipe(r))

# Per-filter: villages and blocks from the filtered pool
pool_df      = df[df['Farm ID'].isin(pool_ids)]
pool_villages = pool_df['Kharif 25 Village'].nunique()
pool_blocks   = pool_df['Kharif 25 Block'].nunique()

# Each filter shows its own 4 chips: filtered farms, villages in filter, blocks in filter, key stat
chip_configs = {
    "🌾 All farms":       (c_all,      c_villages,    c_blocks,    c_meter,    "With Meter"),
    "💧 Has water meter": (c_meter,    pool_villages, pool_blocks, c_active,   "Active Meter"),
    "🚫 No water meter":  (c_no_meter, pool_villages, pool_blocks, c_no_meter, "No Meter"),
    "✅ Active meter":    (c_active,   pool_villages, pool_blocks, c_active,   "Active"),
    "⛔ Inactive meter":  (c_inactive, pool_villages, pool_blocks, c_inactive, "Inactive"),
    "🔧 Has PVC pipes":   (c_pipe,     pool_villages, pool_blocks, c_pipe,     "With Pipes"),
    "🪣 No PVC pipes":    (c_no_pipe,  pool_villages, pool_blocks, c_no_pipe,  "No Pipes"),
}
chip1, chip2, chip3, chip4_num, chip4_lbl = chip_configs.get(
    filter_opt, (c_all, c_villages, c_blocks, c_meter, "With Meter"))

# Labels for chip 1
chip1_labels = {
    "🌾 All farms":       "Total Farms",
    "💧 Has water meter": "With Meter",
    "🚫 No water meter":  "No Meter",
    "✅ Active meter":    "Active Meter",
    "⛔ Inactive meter":  "Inactive Meter",
    "🔧 Has PVC pipes":   "With Pipes",
    "🪣 No PVC pipes":    "No Pipes",
}
chip1_lbl = chip1_labels.get(filter_opt, "Total Farms")

# #4: Fixed project title — never changes
st.markdown(f"""
<div class="proj-header">
  <h1>🌾 Digital Village Project</h1>
  <div class="sub">Kharif 2025 Farm Intelligence &nbsp;·&nbsp; Tel Aviv University | Thapar University, Patiala</div>
  <div class="credits">Research Lead: <b>Dan Uriel Etgar</b> &nbsp;·&nbsp; Dashboard: <b>Satyam Yadav</b> (Lead Research Assistant)</div>
</div>
<div class="stat-row">
  <div class="stat-chip"><div class="num">{chip1}</div><div class="lbl">{chip1_lbl}</div></div>
  <div class="stat-chip"><div class="num">{chip2}</div><div class="lbl">Villages</div></div>
  <div class="stat-chip"><div class="num">{chip3}</div><div class="lbl">Blocks</div></div>
  <div class="stat-chip"><div class="num" style="color:#3fb950">{chip4_num}</div><div class="lbl">{chip4_lbl}</div></div>
</div>
<div class="farm-header">
  <div class="fid">Selected Farm</div>
  <h2>{v(row,'Farm ID')}</h2>
  <div class="meta">👤 {farmer_name} &nbsp;·&nbsp; 📞 {farmer_phone} &nbsp;·&nbsp; 🏘️ {village}, {block}</div>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1.05, 1], gap="medium")

# ── LEFT ─────────────────────────────────────────────────────────────────────
with col1:

    st.markdown('<div class="sec">📋 Farm Details</div>', unsafe_allow_html=True)
    rows = [kv_row("Farm ID", v(row,'Farm ID')),
            kv_row("Farmer",  farmer_name),
            kv_row("Phone",   farmer_phone),
            kv_row("Village", village),
            kv_row("Block",   block)]
    loc = v(row, 'Kharif 25 Locations')
    if loc: rows.append(kv_row("Location", loc))
    st.markdown(f'<div class="card"><div class="card-title">Basic Information</div>{"".join(rows)}</div>', unsafe_allow_html=True)

    st.markdown('<div class="sec">🌿 Kharif 2025 Season</div>', unsafe_allow_html=True)
    rows = []
    acres = v(row, 'Kharif 25 Acres farm / farmer reporting')
    if acres: rows.append(kv_row("Acres", acres))
    rows.append(kv_row("Paddy Rice", badge(v(row,'Kharif 25 Paddy Rice (Y/N)'))))
    nursery    = clean_date(v(row,'Kharif 25 Nursary sowing (TPR) and DSR sowing - Date'))
    transplant = clean_date(v(row,'Kharif 25 Paddy transplanting date (TPR)'))
    harvest    = clean_date(v(row,'Kharif 25 Paddy Harvest date'))
    if nursery:    rows.append(kv_row("Nursery/Sowing", nursery))
    if transplant: rows.append(kv_row("Transplanting",  transplant))
    if harvest:    rows.append(kv_row("Harvest",        harvest))
    st.markdown(f'<div class="card"><div class="card-title">Season Data</div>{"".join(rows)}</div>', unsafe_allow_html=True)

    st.markdown('<div class="sec">📊 Studies</div>', unsafe_allow_html=True)
    studies = [('TPR Study','Kharif 25 / TPR Group Study (Y/N)'),
               ('DSR Study','Kharif 25 / DSR farm Study (Y/N)'),
               ('RC Study', 'Kharif 25 / Remote Controllers study (Y/N)'),
               ('AWD Study','Kharif 25 / AWD Study (Y/N)')]
    rows = [kv_row(k, badge(v(row,c))) for k,c in studies]
    st.markdown(f'<div class="card"><div class="card-title">Research Groups</div>{"".join(rows)}</div>', unsafe_allow_html=True)

    # Meter section — only shown if farm has a meter (#1, #3)
    inst = clean_date(v(row,'Kharif 25 meter installation date'))
    rem  = clean_date(v(row,'Kharif 25 meter remove date'))
    if has_meter(row):
        st.markdown('<div class="sec">💧 Water Meters</div>', unsafe_allow_html=True)
        rows = [kv_row("Monitoring", badge(v(row,'Kharif 25 Meter monitoring (Y/N) was done at any stage of the season')))]
        if inst: rows.append(kv_row("Installed", inst))
        if rem:  rows.append(kv_row("Removed", rem))
        for i in [1, 2]:
            ser  = v(row, f'Kharif 25 Meter serial number / {i}')
            locm = v(row, f'Kharif 25 Meter location / {i}')
            act  = v(row, f'Kharif 25 Meter active / {i} (Y/N)')
            if ser or locm:
                drows = [dkv_row("Active", badge(act))]
                if ser:  drows.append(dkv_row("Serial",   ser,  code=True))
                if locm: drows.append(dkv_row("Location", locm, code=True))
                st.markdown(f'<div class="dev-card"><div class="dev-title">💧 Water Meter {i}</div>{"".join(drows)}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="dev-card" style="color:#8b949e;font-size:0.82rem">No meter installed</div>', unsafe_allow_html=True)

    st.markdown('<div class="sec">🔧 PVC Pipes</div>', unsafe_allow_html=True)
    pipe_mon = v(row,'Kharif 25 PVC Pipe monitoring (Y/N)')
    st.markdown(f'<div style="margin-bottom:6px;font-size:0.82rem;color:#8b949e">Monitoring: {badge(pipe_mon)}</div>', unsafe_allow_html=True)
    found_p = False
    for i in [1,2,3,4,5]:
        code  = v(row, f'Kharif 25 PVC Pipe code / {i}')
        loc_p = v(row, f'Kharif 25 PVC Pipe location / {i}')
        if code or loc_p:
            found_p = True
            # #2: include farmer info in each pipe card
            drows = [
                dkv_row("Farm",    v(row,'Farm ID'),  code=True),
                dkv_row("Farmer",  farmer_name),
                dkv_row("Phone",   farmer_phone),
            ]
            if code:  drows.append(dkv_row("Code",     code,  code=True))
            if loc_p: drows.append(dkv_row("Location", loc_p, code=True))
            st.markdown(f'<div class="dev-card"><div class="dev-title">🔧 Pipe {i}</div>{"".join(drows)}</div>', unsafe_allow_html=True)
    if not found_p:
        st.markdown('<div class="dev-card" style="color:#8b949e;font-size:0.82rem">No pipes installed</div>', unsafe_allow_html=True)


# ── MAP ───────────────────────────────────────────────────────────────────────
with col2:
    st.markdown('<div class="sec">🗺️ Farm Map</div>', unsafe_allow_html=True)

    polygon_raw  = str(row.get('polygons','')).strip()
    tubewell_raw = str(row.get('tw location','')).strip()
    polygon_coords = parse_polygon(polygon_raw) if polygon_raw not in('','nan','None') else []
    tubewell_coord = parse_any(tubewell_raw)    if tubewell_raw not in('','nan','None') else None

    # #1 & #3: collect meter locations — use these ON MAP instead of tubewell
    meter_locations = {}
    for i in [1,2]:
        mloc = v(row,f'Kharif 25 Meter location / {i}')
        mser = v(row,f'Kharif 25 Meter serial number / {i}')
        if mloc and mser:
            mc = parse_any(mloc)
            if mc:
                meter_locations[i] = {'coord': mc, 'serial': mser,
                                       'active': v(row,f'Kharif 25 Meter active / {i} (Y/N)')}

    # Map center: polygon > first meter > tubewell
    if polygon_coords:
        clat = sum(c[0] for c in polygon_coords)/len(polygon_coords)
        clon = sum(c[1] for c in polygon_coords)/len(polygon_coords)
    elif meter_locations:
        clat,clon = list(meter_locations.values())[0]['coord']
    elif tubewell_coord:
        clat,clon = tubewell_coord
    else:
        clat,clon = 30.41,76.42

    # #4: no location data at all
    if not polygon_coords and not tubewell_coord and not meter_locations:
        st.markdown("""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:12px;
             padding:40px 24px;text-align:center;margin-top:10px">
          <div style="font-size:2.5rem;margin-bottom:12px">📭</div>
          <div style="color:#e6edf3;font-size:1.05rem;font-weight:600;margin-bottom:8px">Location Data Unavailable</div>
          <div style="color:#8b949e;font-size:0.84rem;line-height:1.6">
            This farm record exists in the Farm Master sheet<br>
            but has no matching location data in Libertalia.<br><br>
            <span style="color:#58a6ff">Farm details above are still complete.</span>
          </div>
        </div>""", unsafe_allow_html=True)
        st.stop()

    m = folium.Map(location=[clat,clon], zoom_start=16, tiles="OpenStreetMap")
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri', name='Satellite', overlay=False, control=True
    ).add_to(m)
    try:
        from folium.plugins import LocateControl
        LocateControl(position='topleft', flyTo=True, locateOptions={"enableHighAccuracy":True}).add_to(m)
    except: pass

    css = "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:13px;min-width:210px;color:#24292f"

    def nav_btn(lat, lon):
        return (f'<a href="https://www.google.com/maps/dir/?api=1&destination={lat},{lon}" '
                f'target="_blank" style="display:inline-block;background:#238636;color:#fff;'
                f'padding:5px 12px;border-radius:6px;text-decoration:none;font-size:12px;'
                f'font-weight:600;margin-top:8px">🧭 Navigate here</a>')

    def popup_row(k, val):
        return (f'<tr><td style="color:#6e7781;padding:3px 4px 3px 0;white-space:nowrap;vertical-align:top">{k}</td>'
                f'<td style="padding:3px 0 3px 10px;font-weight:500;text-align:right">{val}</td></tr>')

    def make_popup(hcolor, htitle, rh, lat, lon, mw=290):
        html = (f'<div style="{css}"><div style="background:{hcolor};color:#fff;padding:8px 10px;'
                f'border-radius:6px 6px 0 0;margin:-9px -9px 10px;font-weight:700">{htitle}</div>'
                f'<table style="width:100%;border-collapse:collapse">{rh}</table>'
                f'{nav_btn(lat,lon)}</div>')
        return folium.Popup(html, max_width=mw)

    if polygon_coords:
        rh  = popup_row("Farmer",    farmer_name)
        rh += popup_row("Phone",     farmer_phone)
        rh += popup_row("Village",   village)
        rh += popup_row("Block",     block)
        ac = v(row,'Kharif 25 Acres farm / farmer reporting')
        if ac: rh += popup_row("Acres", ac)
        tp = clean_date(v(row,'Kharif 25 Paddy transplanting date (TPR)'))
        hv = clean_date(v(row,'Kharif 25 Paddy Harvest date'))
        if tp: rh += popup_row("Transplant", tp)
        if hv: rh += popup_row("Harvest", hv)
        folium.Polygon(locations=polygon_coords, color='#2ea043', fill=True,
            fill_color='#3fb950', fill_opacity=0.25, weight=2.5,
            tooltip="🌾 Click for farm details",
            popup=make_popup('#0a3d1f', f'🌾 {v(row,"Farm ID")}', rh, clat, clon)
        ).add_to(m)

    if tubewell_coord:
        rh  = popup_row("Farm",    v(row,'Farm ID'))
        rh += popup_row("Farmer",  farmer_name)
        rh += popup_row("Phone",   farmer_phone)
        rh += popup_row("Village", village)
        rh += popup_row("Block",   block)
        ac = v(row,'Kharif 25 Acres farm / farmer reporting')
        if ac: rh += popup_row("Acres", ac)
        rh += popup_row("Meter(s)", f'<span style="color:#3fb950;font-weight:600">{", ".join(d["serial"] for d in meter_locations.values()) or "—"}</span>')
        rh += popup_row("Lat", f"{tubewell_coord[0]:.6f}°N")
        rh += popup_row("Lon", f"{tubewell_coord[1]:.6f}°E")
        # #1: only show tubewell pin if NO meter installed
        if not meter_locations:
            folium.Marker(location=tubewell_coord, tooltip="💧 Tubewell (no meter)",
                popup=make_popup('#0d2137','💧 Tubewell',rh,*tubewell_coord),
                icon=folium.Icon(color='blue',icon='tint',prefix='fa')).add_to(m)

    # #1 & #3: show BOTH meters at their own locations (purple pins)
    for i, mdata in meter_locations.items():
        mc   = mdata['coord']
        mser = mdata['serial']
        mact = mdata['active']
        rh  = popup_row("Serial", f'<b>{mser}</b>')
        rh += popup_row("Active", mact)
        rh += popup_row("Farmer", farmer_name)
        rh += popup_row("Phone",  farmer_phone)
        rh += popup_row("Lat", f"{mc[0]:.6f}°N")
        rh += popup_row("Lon", f"{mc[1]:.6f}°E")
        folium.Marker(location=mc, tooltip=f"🟣 Meter {i}: {mser}",
            popup=make_popup('#4a0080',f'🟣 Water Meter {i}',rh,*mc,mw=260),
            icon=folium.Icon(color='purple',icon='tint',prefix='fa')).add_to(m)

    # #2: PVC Pipes — custom pipe emoji icon
    for i in [1,2,3,4,5]:
        ploc  = v(row,f'Kharif 25 PVC Pipe location / {i}')
        pcode = v(row,f'Kharif 25 PVC Pipe code / {i}')
        if ploc:
            pc = parse_any(ploc)
            if pc:
                rh  = popup_row("Code",   f'<b>{pcode}</b>')
                rh += popup_row("Farmer", farmer_name)
                rh += popup_row("Phone",  farmer_phone)
                rh += popup_row("Lat",    f"{pc[0]:.6f}°N")
                rh += popup_row("Lon",    f"{pc[1]:.6f}°E")
                pipe_icon = folium.DivIcon(
                    html=('<div style="background:#c0392b;color:white;border-radius:50%;'
                          'width:26px;height:26px;display:flex;align-items:center;'
                          'justify-content:center;font-size:13px;border:2px solid #fff;'
                          'box-shadow:0 2px 4px rgba(0,0,0,0.5)">🪧</div>'),
                    icon_size=(26,26), icon_anchor=(13,13)
                )
                folium.Marker(location=pc, tooltip=f"🔴 Pipe {i}: {pcode}",
                    popup=make_popup('#7b0000',f'🔴 PVC Pipe {i}',rh,*pc,mw=230),
                    icon=pipe_icon).add_to(m)

    folium.LayerControl().add_to(m)
    st_folium(m, width=None, height=490, returned_objects=[])

    # Dynamic legend
    parts = ['<span style="color:#3fb950">■</span> Farm Polygon'] if polygon_coords else []
    if tubewell_coord and not meter_locations:
        parts.append('<span style="color:#58a6ff">●</span> Tubewell')
    if meter_locations:
        parts.append('<span style="color:#9b59b6">●</span> Water Meter')
    if any(parse_any(v(row,f'Kharif 25 PVC Pipe location / {i}')) for i in[1,2,3,4,5]):
        parts.append('<span style="color:#f85149">🪧</span> PVC Pipe')
    if parts:
        st.markdown(f'<div style="background:#161b22;border:1px solid #21262d;border-radius:8px;padding:8px 14px;font-size:0.8rem;color:#8b949e;margin-top:6px">{"&nbsp;&nbsp;".join(parts)}</div>', unsafe_allow_html=True)

    rows_c = [kv_row("Center", f"{clat:.5f}°N, {clon:.5f}°E")]
    nav_link = (f'<a href="https://www.google.com/maps/dir/?api=1&destination={clat},{clon}" '
                f'target="_blank" style="background:#238636;color:#fff;padding:6px 14px;border-radius:6px;'
                f'text-decoration:none;font-size:0.82rem;font-weight:600;display:inline-block;margin-top:8px">'
                f'🧭 Open in Google Maps</a>')
    st.markdown(f'<div class="card" style="margin-top:8px"><div class="card-title">Coordinates &amp; Navigation</div>{"".join(rows_c)}{nav_link}</div>', unsafe_allow_html=True)

st.markdown(f'<hr style="border-color:#21262d;margin:20px 0"><p style="color:#484f58;font-size:0.76rem;text-align:center">🌍 Digital Village Project &nbsp;·&nbsp; Tel Aviv University &amp; Thapar University, Patiala &nbsp;·&nbsp; Research Lead: Dan Uriel Etgar &nbsp;·&nbsp; Dashboard: Satyam Yadav &nbsp;·&nbsp; {len(df)} farms</p>', unsafe_allow_html=True)
