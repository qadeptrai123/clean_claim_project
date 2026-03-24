"""
claims_editor.py  —  Web-based Claims Editor (Flask)
Mini app chạy bằng Flask, mở trình duyệt tự động.
Hiển thị raw JSON, edit trực tiếp, save về file.

Cài đặt:  pip install flask
Chạy:     python cleaner/claims_editor.py
           python cleaner/claims_editor.py claims_formatted.json
"""

import json
import sys
import webbrowser
from pathlib import Path
from threading import Timer

from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template_string,
    request,
    send_file,
)

# ─────────────────────────────────────────────────────────────────────────────
PORT = 5555
app = Flask(__name__)
app.config["JSON_PATH"] = ""


@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    traceback.print_exc()
    return f"<pre>{traceback.format_exc()}</pre>", 500


def load_records():
    with open(app.config["JSON_PATH"], encoding="utf-8") as f:
        return json.load(f)


def save_records(data):
    with open(app.config["JSON_PATH"], "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _resolve_media_path(rel_path: str) -> Path | None:
    if not rel_path:
        return None
    normalized = rel_path.replace("\\", "/").lstrip("/")
    roots = [
        Path(__file__).parent.parent,
        Path(app.config["JSON_PATH"]).parent,
    ]
    for root in roots:
        candidate = (root / normalized).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            continue
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


@app.route("/media-file")
def media_file():
    rel_path = request.args.get("path", "")
    resolved = _resolve_media_path(rel_path)
    if resolved is None:
        abort(404)
    return send_file(resolved)


# ─────────────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    records = load_records()
    total = len(records)

    stats = {"total": 0, "SUPPORTED": 0, "REFUTED": 0, "NOT_ENOUGH_INFO": 0}
    for rec in records:
        for k, v in rec.get("claims", {}).items():
            if k in stats:
                stats[k] += len(v)
                stats["total"] += len(v)

    # Build sidebar items
    sidebar_items = []
    for i, rec in enumerate(records):
        c = rec.get("claims", {})
        s = len(c.get("SUPPORTED", []))
        r = len(c.get("REFUTED", []))
        n = len(c.get("NOT_ENOUGH_INFO", []))
        total_c = s + r + n
        sidebar_items.append({
            "index": i,
            "id": rec.get("id", i + 1),
            "total": total_c,
            "s": s, "r": r, "n": n,
        })

    return render_template_string(TEMPLATE,
                                  sidebar_items=sidebar_items,
                                  stats=stats,
                                  total=total)


@app.route("/record/<int:idx>")
def record_page(idx):
    records = load_records()
    if not (0 <= idx < len(records)):
        abort(404)

    rec = records[idx]
    total = len(records)

    stats = {"total": 0, "SUPPORTED": 0, "REFUTED": 0, "NOT_ENOUGH_INFO": 0}
    for k, v in rec.get("claims", {}).items():
        if k in stats:
            stats[k] += len(v)
            stats["total"] += len(v)

    # Serialize claims for JS (json.dumps → safe JS value)
    claims_json = json.dumps(rec.get("claims", {}), ensure_ascii=False)

    return render_template_string(
        RECORD_TEMPLATE,
        rec=rec,
        idx=idx,
        total=total,
        stats=stats,
        claims_json=claims_json,
        json=json,
    )


@app.route("/api/record/<int:idx>", methods=["GET"])
def api_get(idx):
    records = load_records()
    if not (0 <= idx < len(records)):
        abort(404)
    return jsonify(records[idx])


@app.route("/api/record/<int:idx>", methods=["POST"])
def api_save(idx):
    records = load_records()
    if not (0 <= idx < len(records)):
        abort(404)
    updated = request.get_json()
    records[idx] = updated
    save_records(records)
    return jsonify({"ok": True, "id": updated.get("id", idx + 1)})


# ─────────────────────────────────────────────────────────────────────────────
# HTML — Homepage (sidebar + welcome)
# ─────────────────────────────────────────────────────────────────────────────
TEMPLATE = """\
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Claims Editor</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: #0d1117; color: #e6edf3;
  font-family: Consolas, Courier New, monospace;
  font-size: 14px; min-height: 100vh;
}
.topbar {
  background: #161b22; border-bottom: 1px solid #30363d;
  padding: 10px 20px; display: flex; align-items: center; gap: 16px;
  flex-wrap: wrap; position: sticky; top: 0; z-index: 10;
}
h1 { font-size: 20px; color: #58a6ff; }
.stats { font-size: 12px; color: #8b949e; }
.stats .s { color: #3fb950; }
.stats .r { color: #f85149; }
.stats .n { color: #d29922; }

.layout { display: flex; min-height: calc(100vh - 52px); }

.sidebar {
  width: 220px; min-width: 220px;
  background: #161b22; border-right: 1px solid #30363d;
  overflow-y: auto; max-height: calc(100vh - 52px);
}
.sb-title {
  padding: 8px 12px 6px; font-size: 11px; color: #8b949e;
  text-transform: uppercase; letter-spacing: 1px;
  border-bottom: 1px solid #21262d; position: sticky; top: 0; background: #161b22;
}
.rec-item {
  padding: 7px 12px; cursor: pointer;
  border-bottom: 1px solid #21262d; font-size: 12px;
  display: flex; align-items: center; gap: 6px;
}
.rec-item:hover { background: #1f2937; }
.rec-item.active { background: #1f6feb22; border-left: 2px solid #1f6feb; }
.rid { color: #58a6ff; min-width: 30px; }
.cnt { margin-left: auto; font-size: 11px; color: #8b949e; }

.main { flex: 1; display: flex; align-items: center; justify-content: center;
        padding: 40px; text-align: center; color: #8b949e; }
.welcome { font-size: 16px; }
.welcome small { color: #484f58; }
.emoji { font-size: 40px; margin-bottom: 12px; }
</style>
</head>
<body>

<div class="topbar">
  <h1>&#128203; Claims Editor</h1>
  <div class="stats">
    Total: <b>{{ stats.total }}</b>
    &nbsp; &#10004; <span class="s">{{ stats.SUPPORTED }}</span>
    &nbsp; &#10008; <span class="r">{{ stats.REFUTED }}</span>
    &nbsp; &#10067; <span class="n">{{ stats.NOT_ENOUGH_INFO }}</span>
  </div>
</div>

<div class="layout">
  <div class="sidebar">
    <div class="sb-title">Records ({{ total }})</div>
    {% for item in sidebar_items %}
    <div class="rec-item" onclick="location.href='/record/{{ item.index }}'">
      <span class="rid">#{{ item.id }}</span>
      {% if item.s %}<span style="color:#3fb950">S{{ item.s }}</span>{% endif %}
      {% if item.r %}<span style="color:#f85149">R{{ item.r }}</span>{% endif %}
      {% if item.n %}<span style="color:#d29922">N{{ item.n }}</span>{% endif %}
      <span class="cnt">{{ item.total }}</span>
    </div>
    {% endfor %}
  </div>

  <div class="main">
    <div class="welcome">
      <div class="emoji">&#128203;</div>
      Click a record on the left panel to start editing.<br>
      <small>Chọn 1 record ở thanh bên trái để chỉnh sửa.</small>
    </div>
  </div>
</div>

</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# HTML — Record Editor Page
# ─────────────────────────────────────────────────────────────────────────────
RECORD_TEMPLATE = """\
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Record #{{ rec.id }} — Claims Editor</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: #0d1117; color: #e6edf3;
  font-family: Consolas, Courier New, monospace;
  font-size: 14px; min-height: 100vh;
}

/* TOPBAR */
.topbar {
  background: #161b22; border-bottom: 1px solid #30363d;
  padding: 10px 16px; display: flex; align-items: center; gap: 12px;
  flex-wrap: wrap; position: sticky; top: 0; z-index: 10;
}
h1 { font-size: 20px; color: #58a6ff; }
.btn {
  background: #21262d; color: #c9d1d9; border: 1px solid #30363d;
  padding: 5px 12px; border-radius: 6px; cursor: pointer;
  font-family: inherit; font-size: 12px; text-decoration: none;
  display: inline-block;
}
.btn:hover { background: #30363d; }
.btn-save {
  background: #1f6feb; color: #fff; border: none;
  padding: 7px 18px; border-radius: 6px; cursor: pointer;
  font-family: inherit; font-size: 12px; font-weight: bold;
  margin-left: auto;
}
.btn-save:hover { background: #388bfd; }

/* NAV */
.rec-nav {
  background: #161b22; border-bottom: 1px solid #30363d;
  padding: 7px 16px; display: flex; align-items: center; gap: 10px;
  font-size: 12px; position: sticky; top: 47px; z-index: 9;
}
.rec-title { color: #58a6ff; font-weight: bold; }
.meta { color: #8b949e; }

/* LAYOUT */
.layout { display: flex; }
.content { flex: 1; padding: 0 0 60px; overflow: auto; }

/* SECTIONS */
.section {
  margin: 14px; background: #161b22;
  border: 1px solid #30363d; border-radius: 6px; overflow: hidden;
}
.section-hdr {
  background: #1c2128; padding: 8px 14px;
  font-size: 11px; font-weight: bold; color: #8b949e;
  text-transform: uppercase; letter-spacing: 1px;
  border-bottom: 1px solid #30363d;
  display: flex; align-items: center; gap: 10px;
}

/* FIELDS */
.field-row {
  display: grid; grid-template-columns: 110px 1fr;
  border-bottom: 1px solid #21262d;
}
.field-key {
  padding: 8px 12px; color: #79c0ff; background: #0d1117;
  font-size: 14px; border-right: 1px solid #21262d;
  display: flex; align-items: flex-start; padding-top: 8px;
}
.field-val { padding: 4px 8px; background: #0d1117; }

textarea, input[type=text] {
  background: #0d1117; color: #e6edf3; border: 1px solid #30363d;
  border-radius: 4px; width: 100%; font-family: Consolas, monospace;
  font-size: 14px; padding: 8px 10px; resize: vertical;
  outline: none; box-sizing: border-box; display: block;
}
textarea:focus, input[type=text]:focus { border-color: #1f6feb; }
textarea[readonly] { opacity: 0.6; }

/* CLAIMS */
.label-badge {
  padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: bold;
  display: inline-block;
}
.label-SUPPORTED { background: #23863633; color: #3fb950; }
.label-REFUTED { background: #da363333; color: #f85149; }
.label-NOT_ENOUGH_INFO { background: #d2992233; color: #d29922; }

.claim-block {
  margin: 10px; border: 1px solid #30363d; border-radius: 6px; overflow: hidden;
}
.ev-item {
  margin: 8px 10px; border: 1px solid #30363d;
  border-radius: 4px; overflow: hidden;
}
.ev-type {
  padding: 3px 10px; font-size: 10px; font-weight: bold;
  display: inline-block;
}
.ev-type-TEXT { background: #1f6feb33; color: #58a6ff; }
.ev-type-IMAGE { background: #8957e533; color: #bc8cff; }
.ev-meta {
  padding: 4px 10px; background: #0d1117; font-size: 11px;
  color: #8b949e; border-bottom: 1px solid #21262d;
}
.ev-meta a { color: #58a6ff; }

/* JSON PREVIEW */
.raw-preview {
  background: #0a0e14; border: 1px solid #1f6feb33;
  border-radius: 4px; padding: 10px; margin: 0 12px 12px; overflow-x: auto;
}
.raw-preview pre {
  font-family: Consolas, monospace; font-size: 11px;
  color: #79c0ff; white-space: pre; margin: 0;
}

/* TOAST */
#toast {
  position: fixed; bottom: 20px; right: 20px;
  background: #238636; color: #fff;
  padding: 10px 20px; border-radius: 6px;
  font-size: 14px; display: none; z-index: 999;
  box-shadow: 0 4px 12px #0008;
}
#toast.err { background: #da3633; }
</style>
</head>
<body>

<!-- TOPBAR -->
<div class="topbar">
  <a class="btn" href="/">&#9664; All Records</a>
  <h1>&#128203; Record #{{ rec.id }}</h1>
  <div style="font-size:14px;color:#8b949e;">
    Total: {{ stats.total }}
    &nbsp;&#10004;<span style="color:#3fb950">{{ stats.SUPPORTED }}</span>
    &nbsp;&#10008;<span style="color:#f85149">{{ stats.REFUTED }}</span>
    &nbsp;&#10067;<span style="color:#d29922">{{ stats.NOT_ENOUGH_INFO }}</span>
  </div>
  <button class="btn-save" onclick="saveRecord()">&#128190; Save</button>
</div>

<!-- NAV -->
<div class="rec-nav">
  <span class="rec-title">{{ idx + 1 }} / {{ total }}</span>
  <span class="meta">ID: {{ rec.id }}&nbsp;|&nbsp;Date: {{ rec.date_iso or '—' }}</span>
  <a class="btn" href="/record/{{ idx - 1 if idx > 0 else 0 }}">&#9664; Prev</a>
  <a class="btn" href="/record/{{ idx + 1 if idx < total - 1 else total - 1 }}">Next &#9654;</a>
</div>

<!-- CONTENT -->
<div class="layout">
<div class="content">

  <!-- METADATA -->
  <div class="section">
    <div class="section-hdr">&#9881; Metadata</div>
    <div class="field-row">
      <div class="field-key">id</div>
      <div class="field-val">
        <input type="text" id="f-id" value="{{ rec.id }}" readonly>
      </div>
    </div>
    <div class="field-row">
      <div class="field-key">date_iso</div>
      <div class="field-val">
        <input type="text" id="f-date_iso" value="{{ rec.date_iso or '' }}">
      </div>
    </div>
    <div class="field-row">
      <div class="field-key">media</div>
      <div class="field-val">
        <textarea id="f-media" rows="3">{{ rec.media | tojson(indent=2) }}</textarea>
      </div>
    </div>
    <div class="field-row">
      <div class="field-key">full_text</div>
      <div class="field-val">
        <textarea id="f-full_text" rows="12" style="min-height:280px;">{{ rec.full_text or '' }}</textarea>
      </div>
    </div>

    <div class="field-row">
      <div class="field-key">media preview</div>
      <div class="field-val">
        {% if rec.get('media') and rec.get('media')|length > 0 %}
        <div style="display:flex;gap:10px;flex-wrap:wrap;padding:4px 0;">
          {% for mp in rec.get('media', []) %}
          <a href="/media-file?path={{ mp | urlencode }}" target="_blank" style="text-decoration:none;">
            <img src="/media-file?path={{ mp | urlencode }}"
                 alt="{{ mp }}"
                 onerror="this.style.display='none'; this.nextElementSibling.style.display='block';"
                 style="max-width:360px;max-height:280px;border:1px solid #30363d;border-radius:6px;display:block;">
            <div style="display:none;color:#f85149;font-size:14px;padding:8px 10px;border:1px dashed #f85149;border-radius:4px;max-width:360px;">Không tìm thấy ảnh: {{ mp }}</div>
          </a>
          {% endfor %}
        </div>
        {% else %}
        <div style="color:#8b949e;font-size:14px;padding:6px 0;">Không có media trong record này.</div>
        {% endif %}
      </div>
    </div>
  </div>

  <!-- CLAIMS -->
  <div class="section">
    <div class="section-hdr">&#10067; Claims</div>

    {% for label_key in ['SUPPORTED', 'REFUTED', 'NOT_ENOUGH_INFO'] %}
    {% set claims = rec.claims.get(label_key, []) %}
    {% if claims %}
    <div style="padding:5px 14px;background:#0d1117;border-bottom:1px solid #21262d;
                font-size:14px;color:#8b949e;text-transform:uppercase;letter-spacing:1px;">
      {{ label_key }} — {{ claims|length }} claims
    </div>
    {% for claim in claims %}
    {% set claim_idx = loop.index0 %}
    <div class="claim-block">
      <div style="padding:5px 12px;background:#1c2128;border-bottom:1px solid #30363d;">
        <span class="label-badge label-{{ label_key }}">{{ label_key }} #{{ loop.index }}</span>
      </div>
      <div style="padding:10px 12px;">

        <div style="margin-bottom:8px;">
          <div style="font-size:14px;color:#58a6ff;margin-bottom:3px;">claim</div>
          <textarea class="claim-field"
            data-label="{{ label_key }}"
            data-ci="{{ loop.index0 }}"
            data-field="claim"
            rows="2">{{ claim.get('claim', '') }}</textarea>
        </div>

        <div style="margin-bottom:8px;">
          <div style="font-size:14px;color:#58a6ff;margin-bottom:3px;">image</div>
          <input class="claim-field"
            data-label="{{ label_key }}"
            data-ci="{{ loop.index0 }}"
            data-field="image"
            type="text"
            value="{{ claim.get('image', '') }}"
            placeholder="media/your_image.jpg">
        </div>

        <div style="margin-bottom:8px;">
          <div style="font-size:14px;color:#58a6ff;margin-bottom:3px;">reason</div>
          <textarea class="claim-field"
            data-label="{{ label_key }}"
            data-ci="{{ loop.index0 }}"
            data-field="reason"
            rows="3">{{ claim.get('reason', '') }}</textarea>
        </div>

        {% for ev in claim.get('evidence', []) %}
        <div class="ev-item">
          <span class="ev-type ev-type-{{ ev.type.upper() }}">{{ ev.type.upper() }}</span>
          {% if ev.get('type') == 'text' %}
          <div class="ev-meta">
            url: <a href="{{ ev.get('url', '') }}" target="_blank">{{ (ev.get('url', ''))[:90] }}</a>
          </div>
          {% elif ev.get('type') == 'image' %}
          <div class="ev-meta">
            image_paths: {{ (ev.get('image_paths', [])) | tojson }}
          </div>
          {% if ev.get('image_paths') and ev.get('image_paths')|length > 0 %}
          <div style="padding:8px 10px;background:#0d1117;display:flex;gap:8px;flex-wrap:wrap;">
            {% for p in ev.get('image_paths', []) %}
            <a href="/media-file?path={{ p | urlencode }}" target="_blank" style="text-decoration:none;">
              <img src="/media-file?path={{ p | urlencode }}"
                   alt="{{ p }}"
                   onerror="this.style.display='none'; this.nextElementSibling.style.display='block';"
                   style="max-width:360px;max-height:280px;border:1px solid #30363d;border-radius:6px;display:block;">
              <div style="display:none;color:#f85149;font-size:12px;padding:6px 8px;border:1px dashed #f85149;border-radius:4px;max-width:360px;">Không tìm thấy ảnh: {{ p }}</div>
            </a>
            {% endfor %}
          </div>
          {% endif %}
          {% endif %}
          <div style="padding:6px 10px;background:#0d1117;">
            <div style="font-size:14px;color:#58a6ff;margin-bottom:3px;">quote</div>
            <textarea class="ev-field"
              data-label="{{ label_key }}"
              data-ci="{{ claim_idx }}"
              data-ei="{{ loop.index0 }}"
              rows="3">{{ ev.get('quote', '') }}</textarea>
          </div>
        </div>
        {% endfor %}

      </div>
    </div>
    {% endfor %}
    {% endif %}
    {% endfor %}
  </div>

  <!-- RAW JSON -->
  <div class="section">
    <div class="section-hdr">&#128196; Raw JSON (read-only preview)</div>
    <div class="raw-preview">
      <pre id="json-preview"></pre>
    </div>
  </div>

</div>
</div>

<div id="toast"></div>

<script>
const REC_ID = {{ rec.id }};
const IDX = {{ idx }};
// Pre-serialize the claims data server-side (safe JSON)
const claimsBase = {{ claims_json | safe }};

// ── Sync textarea changes into live JSON preview ──
function syncPreview() {
  const rec = buildRecord();
  document.getElementById('json-preview').textContent =
    JSON.stringify(rec, null, 2);
}

function buildRecord() {
  // Deep-copy claims
  const rec = {
    id: {{ rec.id }},
    date_iso: document.getElementById('f-date_iso').value,
    media: (function() {
      try { return JSON.parse(document.getElementById('f-media').value || '[]'); }
      catch(e) { return []; }
    })(),
    full_text: document.getElementById('f-full_text').value,
    claims: JSON.parse(JSON.stringify(claimsBase)),
  };

  // Merge textarea edits into claims
  document.querySelectorAll('.claim-field').forEach(function(el) {
    var lk = el.dataset.label;
    var ci = parseInt(el.dataset.ci);
    var fk = el.dataset.field;
    if (rec.claims[lk] && rec.claims[lk][ci]) {
      rec.claims[lk][ci][fk] = el.value;
    }
  });

  // Merge evidence quotes
  document.querySelectorAll('.ev-field').forEach(function(el) {
    var lk = el.dataset.label;
    var ci = parseInt(el.dataset.ci);
    var ei = parseInt(el.dataset.ei);
    if (rec.claims[lk] && rec.claims[lk][ci] && rec.claims[lk][ci].evidence && rec.claims[lk][ci].evidence[ei]) {
      rec.claims[lk][ci].evidence[ei].quote = el.value;
    }
  });

  return rec;
}

function saveRecord() {
  var rec = buildRecord();
  fetch('/api/record/' + IDX, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(rec),
  })
  .then(function(r) { return r.json(); })
  .then(function(d) { showToast('Record #' + d.id + ' saved!'); })
  .catch(function(e) { showToast('Save failed: ' + e, true); });
}

function showToast(msg, isErr) {
  var t = document.getElementById('toast');
  t.textContent = msg;
  t.className = isErr ? 'err' : '';
  t.style.display = 'block';
  setTimeout(function() { t.style.display = 'none'; }, 3000);
}

// Init
document.addEventListener('DOMContentLoaded', function() {
  syncPreview();
  document.querySelectorAll('textarea, input').forEach(function(el) {
    el.addEventListener('input', syncPreview);
  });
});
</script>

</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    base = Path(__file__).parent.parent
    json_path = base / "claims_formatted.json"
    if len(sys.argv) >= 2:
        json_path = Path(sys.argv[1])
    if not json_path.exists():
        print("ERROR: File not found:", json_path)
        print("Usage: python", sys.argv[0], "[path_to_claims_formatted.json]")
        sys.exit(1)

    app.config["JSON_PATH"] = str(json_path)

    url = "http://localhost:" + str(PORT)
    print()
    print("  Claims Editor")
    print("  URL:", url)
    print("  File:", json_path)
    print("  Press Ctrl+C to stop")
    print()

    Timer(1.0, lambda: webbrowser.open(url)).start()

    try:
        app.run(host="0.0.0.0", port=PORT, debug=True, use_reloader=False)
    except OSError as e:
        if "Port" in str(e):
            alt = PORT + 1
            print("Port", PORT, "in use — trying", alt)
            app.run(host="0.0.0.0", port=alt, debug=True, use_reloader=False)
        else:
            raise
