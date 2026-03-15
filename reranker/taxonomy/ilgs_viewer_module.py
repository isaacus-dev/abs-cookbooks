
from __future__ import annotations

import html
import json
import uuid
from typing import Any, Callable, Optional

from IPython.display import HTML, display, clear_output


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _short_list(items: list[Any] | None, max_items: int = 2) -> str:
    values = list(items or [])
    if not values:
        return "—"
    shown = ", ".join(str(x) for x in values[:max_items])
    if len(values) > max_items:
        shown += f" +{len(values) - max_items}"
    return shown


def _party_name(party: Any) -> str:
    if isinstance(party, dict):
        return str(party.get("name") or "Unnamed party")
    return str(party)


def _to_jsonable(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    # Pydantic v2
    if hasattr(obj, "model_dump"):
        try:
            return _to_jsonable(obj.model_dump())
        except Exception:
            pass
    # Pydantic v1
    if hasattr(obj, "dict"):
        try:
            return _to_jsonable(obj.dict())
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        try:
            # drop private attrs
            return {
                k: _to_jsonable(v)
                for k, v in vars(obj).items()
                if not k.startswith("_")
            }
        except Exception:
            pass
    return str(obj)


def _record_for_json(record: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in record.items():
        if k == "enriched_doc":
            out[k] = _to_jsonable(v)
        else:
            out[k] = _to_jsonable(v)
    return out


def _build_rows_html(records: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for i, record in enumerate(records):
        title = record.get("pretty_title") or record.get("title") or record.get("source_name") or "Untitled"
        category = (record.get("category") or {}).get("label", "—")
        date_value = record.get("date") or "—"
        parties = record.get("parties", []) or []
        party_names = [_party_name(p) for p in parties]
        locations = record.get("locations", []) or []
        terms = record.get("terms", []) or []
        signatures = record.get("signatures", []) or []
        file_name = record.get("source_name") or "Untitled"
        term_names = [t.get("name", "Unnamed term") if isinstance(t, dict) else str(t) for t in terms]

        rows.append(
            f"""
            <tr>
              <td><button class="mv-link mv-title" data-action="preview" data-row="{i}">{_esc(title)}</button><div class="mv-category">{_esc(category)}</div></td>
              <td><button class="mv-link" data-action="parties" data-row="{i}">{_esc(_short_list(party_names, 2))}</button></td>
              <td><button class="mv-link" data-action="locations" data-row="{i}">{_esc(_short_list(locations, 2))}</button></td>
              <td><button class="mv-link" data-action="terms" data-row="{i}">{_esc(_short_list(term_names, 2))}</button></td>
              <td><button class="mv-link" data-action="signatures" data-row="{i}">{_esc(_short_list(signatures, 1))}</button></td>
              <td>{_esc(date_value)}</td>
              <td>{_esc(file_name)}</td>
            </tr>
            """
        )

    if not rows:
        rows.append('<tr><td colspan="7" style="padding:24px;color:#94a0b3;text-align:left;">No documents loaded.</td></tr>')
    return "".join(rows)


HTML_TEMPLATE = """
<div class="mv-root" id="__ROOT_ID__">
  <style>
    @import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap");

    .mv-root {
      --bg:#f7f9fc; --surface:#fff; --surface2:#fafcff; --border:#e6ecf3; --text:#132033; --muted:#68768b;
      --blue:#255cff; --blue-soft:#eef4ff; --shadow:0 12px 34px rgba(15,23,42,0.08);
      --font-scale: 1.15;
      font-family:Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color:var(--text); width:100%; max-width:100%; position:relative; box-sizing:border-box;
      font-size:calc(14px * var(--font-scale)); text-align:left;
    }

    .mv-shell { border:1px solid var(--border); border-radius:18px; background:var(--surface); box-shadow:var(--shadow); overflow:hidden; }
    .mv-header { display:flex; justify-content:space-between; align-items:center; gap:12px; padding:18px 18px; border-bottom:1px solid var(--border); text-align:left; }
    .mv-header h3 { margin:0; font-size:calc(18px * var(--font-scale)); font-weight:650; text-align:left; }
    .mv-header p { margin:5px 0 0; color:var(--muted); font-size:calc(13px * var(--font-scale)); text-align:left; }
    .mv-pill { display:inline-flex; align-items:center; padding:7px 11px; border-radius:999px; background:var(--blue-soft); color:#2448b6; font-size:calc(12px * var(--font-scale)); font-weight:700; }
    .mv-btn { border:0; border-radius:12px; padding:10px 13px; background:#f2f5fa; color:#4f6075; font-size:calc(13px * var(--font-scale)); font-weight:650; cursor:pointer; }

    .mv-table-wrap { overflow:auto; max-height:1260px; min-height:720px; background:var(--bg); }
    .mv-table { width:100%; min-width:1000px; border-collapse:separate; border-spacing:0; table-layout:fixed; background:var(--surface); }
    .mv-table thead th {
      position:sticky; top:0; background:rgba(255,255,255,.96); border-bottom:1px solid var(--border);
      padding:15px 12px; text-align:left; color:var(--muted); font-size:calc(12px * var(--font-scale));
      font-weight:700; text-transform:uppercase;
    }
    .mv-table td {
      padding:15px 12px; border-bottom:1px solid var(--border); vertical-align:top;
      font-size:calc(14px * var(--font-scale)); line-height:1.55; text-align:left;
    }
    .mv-table tbody tr:hover { background:#f9fbff; }
    .mv-link {
      background:none; border:0; padding:0; color:#1e4ed1; cursor:pointer; font:inherit;
      text-align:left; display:inline-block;
    }
    .mv-title { font-weight:650; font-size:calc(14px * var(--font-scale)); }
    .mv-category { display:inline-flex; margin-top:8px; padding:5px 9px; border-radius:999px; background:var(--blue-soft); color:#2448b6; font-size:calc(12px * var(--font-scale)); font-weight:700; }

    .mv-overlay { position:absolute; inset:0; display:none; align-items:center; justify-content:center; padding:16px; background:rgba(10,15,24,0.18); z-index:20; box-sizing:border-box; }
    .mv-overlay.open { display:flex; }
    .mv-modal { width:min(1400px,100%); max-height:92%; overflow:hidden; background:var(--surface); border:1px solid var(--border); border-radius:18px; box-shadow:0 24px 80px rgba(15,23,42,.18); display:flex; flex-direction:column; }
    .mv-modal-head { display:flex; justify-content:space-between; align-items:center; padding:18px 18px; border-bottom:1px solid var(--border); text-align:left; }
    .mv-modal-head h4 { margin:0; font-size:calc(17px * var(--font-scale)); font-weight:650; text-align:left; }
    .mv-modal-close { width:32px; height:32px; border:0; border-radius:999px; background:#f2f5fa; cursor:pointer; font-size:calc(20px * var(--font-scale)); }
    .mv-modal-body { padding:0; overflow:auto; text-align:left; }

    .mv-basic-modal-body { padding:18px; overflow:auto; }
    .mv-card { border:1px solid var(--border); border-radius:14px; padding:15px; background:var(--surface2); margin-bottom:12px; text-align:left; }
    .mv-card-title { font-size:calc(14px * var(--font-scale)); font-weight:650; margin-bottom:8px; text-align:left; }
    .mv-card-text { font-size:calc(14px * var(--font-scale)); line-height:1.65; color:#334156; white-space:pre-wrap; text-align:left; }

    .mv-party-card { border:1px solid var(--border); border-radius:14px; padding:15px; background:var(--surface2); margin-bottom:12px; text-align:left; }
    .mv-party-head { display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:8px; justify-content:flex-start; }
    .mv-party-name { font-size:calc(15px * var(--font-scale)); font-weight:650; color:var(--text); text-align:left; }
    .mv-role-pill { display:inline-flex; align-items:center; padding:5px 10px; border-radius:999px; font-size:calc(12px * var(--font-scale)); font-weight:700; border:1px solid transparent; }
    .mv-party-meta { font-size:calc(13px * var(--font-scale)); color:var(--muted); text-align:left; }

    .mv-map-layout { display:grid; grid-template-columns:260px 1fr; gap:14px; align-items:start; padding:18px; }
    .mv-location-list button {
      display:block; width:100%; text-align:left; border:0; background:var(--surface2); padding:10px;
      border-radius:10px; margin-bottom:6px; cursor:pointer; font:inherit;
    }
    .mv-map-frame { width:100%; height:340px; border:1px solid var(--border); border-radius:14px; background:#fafcff; }

    .ilgs-layout { display:grid; grid-template-columns: 280px minmax(0, 1fr) 360px; gap:0; min-height:72vh; }
    .ilgs-panel { border-right:1px solid var(--border); overflow:auto; }
    .ilgs-panel:last-child { border-right:0; }
    .ilgs-left, .ilgs-right { background:var(--surface2); }
    .ilgs-left { padding:16px 12px 16px 16px; }
    .ilgs-center { background:var(--surface); padding:0; }
    .ilgs-right { padding:16px; }
    .ilgs-section-title { font-size:calc(12px * var(--font-scale)); font-weight:700; text-transform:uppercase; letter-spacing:.03em; color:var(--muted); margin:0 0 10px 0; }
    .ilgs-tree { list-style:none; padding-left:0; margin:0; }
    .ilgs-tree-node { margin:0; }
    .ilgs-tree-btn {
      display:block; width:100%; text-align:left; border:0; background:transparent; padding:8px 10px; border-radius:10px; cursor:pointer;
      font:inherit; color:var(--text);
    }
    .ilgs-tree-btn:hover { background:#eef4ff; color:#2448b6; }
    .ilgs-tree-children { list-style:none; padding-left:14px; margin:0; border-left:1px solid #edf1f6; }
    .ilgs-tree-meta { color:var(--muted); font-size:calc(11px * var(--font-scale)); display:block; margin-top:2px; }

    .ilgs-doc-toolbar {
      display:flex; justify-content:space-between; align-items:center; gap:12px;
      padding:12px 16px; border-bottom:1px solid var(--border); position:sticky; top:0; z-index:2; background:rgba(255,255,255,.96);
    }
    .ilgs-legend { display:flex; gap:8px; flex-wrap:wrap; }
    .ilgs-legend-item {
      display:inline-flex; align-items:center; gap:6px; padding:4px 8px; border-radius:999px; font-size:calc(11px * var(--font-scale)); font-weight:600; background:#f5f7fb;
    }
    .ilgs-doc {
      padding:18px 18px 120px 18px;
      white-space:pre-wrap;
      line-height:1.75;
      font-size:calc(14px * var(--font-scale));
      color:var(--text);
    }
    .ilgs-doc mark, .ilgs-ann {
      border-radius:6px;
      padding:0 .08em;
      cursor:default;
    }
    .ilgs-ann.person { background:rgba(83, 142, 255, 0.16); }
    .ilgs-ann.term { background:rgba(68, 180, 112, 0.18); }
    .ilgs-ann.location { background:rgba(218, 126, 24, 0.18); }
    .ilgs-ann.date { background:rgba(137, 92, 246, 0.17); }
    .ilgs-ann.quote { background:rgba(88, 100, 126, 0.14); }
    .ilgs-ann.xref { background:rgba(255, 214, 87, 0.28); cursor:pointer; text-decoration:underline dotted; }
    .ilgs-anchor { display:block; position:relative; top:-80px; visibility:hidden; height:0; }
    .ilgs-feature-group { margin-bottom:18px; }
    .ilgs-feature-item { border:1px solid var(--border); background:white; border-radius:12px; padding:10px 11px; margin-bottom:10px; }
    .ilgs-feature-name { font-weight:650; font-size:calc(13px * var(--font-scale)); margin-bottom:4px; }
    .ilgs-feature-meta { color:var(--muted); font-size:calc(12px * var(--font-scale)); }
    .ilgs-kv { display:grid; grid-template-columns:110px 1fr; gap:8px; font-size:calc(13px * var(--font-scale)); margin-bottom:8px; }
    .ilgs-kv .k { color:var(--muted); }

    @media (max-width: 1200px) {
      .ilgs-layout { grid-template-columns: 240px minmax(0, 1fr) 300px; }
    }
    @media (max-width: 980px) {
      .mv-table-wrap { min-height:520px; max-height:920px; }
      .mv-map-layout { grid-template-columns:1fr; }
      .mv-map-frame { height:300px; }
      .ilgs-layout { grid-template-columns: 1fr; }
      .ilgs-panel { border-right:0; border-bottom:1px solid var(--border); max-height:none !important; }
    }
  </style>

  <div class="mv-shell">
    <div class="mv-header">
      <div>
        <h3>Document metadata</h3>
        <p>Interactive viewer for preview, parties, locations, terms, and signatures.</p>
      </div>
      <div>
        <span class="mv-pill">__COUNT_LABEL__</span>
        <button class="mv-btn" type="button" id="__EXPORT_ID__">Export JSON</button>
      </div>
    </div>

    <div class="mv-table-wrap">
      <table class="mv-table">
        <thead>
          <tr>
            <th style="width:27%;">Title</th>
            <th style="width:16%;">Parties</th>
            <th style="width:13%;">Locations</th>
            <th style="width:14%;">Terms</th>
            <th style="width:12%;">Signatures</th>
            <th style="width:10%;">Date</th>
            <th style="width:8%;">File</th>
          </tr>
        </thead>
        <tbody>__ROWS_HTML__</tbody>
      </table>
    </div>

    <div class="mv-overlay" id="__OVERLAY_ID__">
      <div class="mv-modal">
        <div class="mv-modal-head">
          <h4 id="__TITLE_ID__">Details</h4>
          <button type="button" class="mv-modal-close" id="__CLOSE_ID__">×</button>
        </div>
        <div class="mv-modal-body" id="__BODY_ID__"></div>
      </div>
    </div>
  </div>

  <script type="application/json" id="__DATA_ID__">__DATA_JSON__</script>
  <script>
    (function() {
      const root = document.getElementById("__ROOT_ID__");
      if (!root) return;

      const records = JSON.parse(root.querySelector("#__DATA_ID__").textContent);
      const overlay = root.querySelector("#__OVERLAY_ID__");
      const modalTitle = root.querySelector("#__TITLE_ID__");
      const modalBody = root.querySelector("#__BODY_ID__");
      const closeBtn = root.querySelector("#__CLOSE_ID__");
      const exportBtn = root.querySelector("#__EXPORT_ID__");

      function esc(value) {
        return String(value ?? "")
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#39;");
      }

      function hashString(text) {
        let hash = 0;
        const value = String(text || "");
        for (let i = 0; i < value.length; i++) {
          hash = ((hash << 5) - hash) + value.charCodeAt(i);
          hash |= 0;
        }
        return Math.abs(hash);
      }

      function roleColor(role) {
        const seed = hashString(role);
        const hue = seed % 360;
        return {
          bg: `hsl(${hue}, 72%, 94%)`,
          fg: `hsl(${hue}, 52%, 34%)`,
          border: `hsl(${hue}, 48%, 78%)`
        };
      }

      function rolePill(role) {
        const label = role || "Unknown role";
        const color = roleColor(label);
        return `<span class="mv-role-pill" style="background:${color.bg};color:${color.fg};border-color:${color.border};">${esc(label)}</span>`;
      }

      function openModal(title, bodyHtml, basic=false) {
        modalTitle.textContent = title;
        modalBody.innerHTML = basic ? `<div class="mv-basic-modal-body">${bodyHtml}</div>` : bodyHtml;
        overlay.classList.add("open");
      }

      function closeModal() {
        overlay.classList.remove("open");
      }

      function cpToCuMap(text) {
        const map = [0];
        let cu = 0;
        for (const ch of text) {
          cu += ch.length;
          map.push(cu);
        }
        return map;
      }

      function sliceCp(text, map, start, end) {
        return text.slice(map[start] || 0, map[end] || 0);
      }

      function spanText(text, map, span) {
        if (!span || span.start == null || span.end == null) return "";
        return sliceCp(text, map, span.start, span.end);
      }

      function hashColor(label) {
        const hue = hashString(label) % 360;
        return `hsl(${hue}, 72%, 94%)`;
      }

      function buildSegmentLabel(seg, text, map) {
        const parts = [];
        if (seg.type_name) parts.push(spanText(text, map, seg.type_name));
        else if (seg.type) parts.push(seg.type);
        if (seg.code) parts.push(spanText(text, map, seg.code));
        if (seg.title) parts.push(spanText(text, map, seg.title));
        const label = parts.filter(Boolean).join(" ").trim();
        if (label) return label;
        return `Segment ${seg.id || ""}`.trim();
      }

      function buildSegmentTree(doc, text, map) {
        const segs = Array.isArray(doc.segments) ? doc.segments : [];
        const byId = new Map();
        segs.forEach(seg => byId.set(seg.id, seg));
        const roots = segs.filter(seg => !seg.parent);

        function renderNode(seg) {
          const children = Array.isArray(seg.children) ? seg.children.map(id => byId.get(id)).filter(Boolean) : [];
          const label = buildSegmentLabel(seg, text, map);
          const meta = [seg.kind, seg.category].filter(Boolean).join(" · ");
          return `
            <li class="ilgs-tree-node">
              <button class="ilgs-tree-btn" data-seg-id="${esc(seg.id || "")}">
                <span>${esc(label)}</span>
                ${meta ? `<span class="ilgs-tree-meta">${esc(meta)}</span>` : ""}
              </button>
              ${children.length ? `<ul class="ilgs-tree-children">${children.map(renderNode).join("")}</ul>` : ""}
            </li>
          `;
        }

        return `<ul class="ilgs-tree">${roots.map(renderNode).join("")}</ul>`;
      }

      function buildFeaturePanel(record, doc, text, map) {
        const persons = Array.isArray(doc.persons) ? doc.persons : [];
        const locations = Array.isArray(doc.locations) ? doc.locations : [];
        const terms = Array.isArray(doc.terms) ? doc.terms : [];
        const dates = Array.isArray(doc.dates) ? doc.dates : [];
        const externalDocs = Array.isArray(doc.external_documents) ? doc.external_documents : [];
        const quotes = Array.isArray(doc.quotes) ? doc.quotes : [];
        const crossrefs = Array.isArray(doc.crossreferences) ? doc.crossreferences : [];

        const personCards = persons.slice(0, 20).map(p => {
          const name = spanText(text, map, p.name) || p.id || "Unnamed person";
          const residence = p.residence || "";
          const type = p.type || "";
          const role = p.role ? String(p.role).replaceAll("_", " ") : "";
          return `
            <div class="ilgs-feature-item">
              <div class="ilgs-feature-name">${esc(name)}</div>
              <div style="margin:6px 0;">${role ? rolePill(role) : ""}</div>
              ${type ? `<div class="ilgs-feature-meta">Type: ${esc(type)}</div>` : ""}
              ${residence ? `<div class="ilgs-feature-meta">Residence: ${esc(residence)}</div>` : ""}
            </div>
          `;
        }).join("");

        const termCards = terms.slice(0, 20).map(t => {
          const name = spanText(text, map, t.name) || t.id || "Unnamed term";
          const meaning = spanText(text, map, t.meaning) || "";
          const mentionCount = Array.isArray(t.mentions) ? t.mentions.length : 0;
          return `
            <div class="ilgs-feature-item">
              <div class="ilgs-feature-name">${esc(name)}</div>
              ${meaning ? `<div class="ilgs-feature-meta">${esc(meaning)}</div>` : ""}
              <div class="ilgs-feature-meta">Mentions: ${mentionCount}</div>
            </div>
          `;
        }).join("");

        const locationCards = locations.slice(0, 20).map(l => {
          const name = spanText(text, map, l.name) || l.id || "Unnamed location";
          const type = l.type || "";
          const jurisdiction = l.jurisdiction || "";
          return `
            <div class="ilgs-feature-item">
              <div class="ilgs-feature-name">${esc(name)}</div>
              ${type ? `<div class="ilgs-feature-meta">Type: ${esc(type)}</div>` : ""}
              ${jurisdiction ? `<div class="ilgs-feature-meta">Jurisdiction: ${esc(jurisdiction)}</div>` : ""}
            </div>
          `;
        }).join("");

        const dateCards = dates.slice(0, 20).map(d => {
          const value = d.value || "";
          const type = d.type || "";
          return `
            <div class="ilgs-feature-item">
              <div class="ilgs-feature-name">${esc(value || "Date")}</div>
              ${type ? `<div class="ilgs-feature-meta">Type: ${esc(type)}</div>` : ""}
            </div>
          `;
        }).join("");

        const extDocCards = externalDocs.slice(0, 15).map(ed => {
          const name = spanText(text, map, ed.name) || ed.id || "External document";
          const type = ed.type || "";
          const jurisdiction = ed.jurisdiction || "";
          return `
            <div class="ilgs-feature-item">
              <div class="ilgs-feature-name">${esc(name)}</div>
              ${type ? `<div class="ilgs-feature-meta">Type: ${esc(type)}</div>` : ""}
              ${jurisdiction ? `<div class="ilgs-feature-meta">Jurisdiction: ${esc(jurisdiction)}</div>` : ""}
            </div>
          `;
        }).join("");

        const quoteCards = quotes.slice(0, 10).map(q => {
          const quoteText = spanText(text, map, q.span || q.quote || q.content) || "";
          const source = q.source_person || q.source_document || "";
          return `
            <div class="ilgs-feature-item">
              <div class="ilgs-feature-meta">${source ? `Source: ${esc(source)}` : "Quote"}</div>
              <div class="ilgs-feature-name" style="font-weight:500;">${esc(quoteText)}</div>
            </div>
          `;
        }).join("");

        return `
          <div class="ilgs-feature-group">
            <div class="ilgs-section-title">Overview</div>
            <div class="ilgs-feature-item">
              <div class="ilgs-kv"><div class="k">Type</div><div>${esc(doc.type || "—")}</div></div>
              <div class="ilgs-kv"><div class="k">Jurisdiction</div><div>${esc(doc.jurisdiction || "—")}</div></div>
              <div class="ilgs-kv"><div class="k">Segments</div><div>${(doc.segments || []).length}</div></div>
              <div class="ilgs-kv"><div class="k">Cross refs</div><div>${crossrefs.length}</div></div>
              <div class="ilgs-kv"><div class="k">Persons</div><div>${persons.length}</div></div>
              <div class="ilgs-kv"><div class="k">Terms</div><div>${terms.length}</div></div>
            </div>
          </div>

          <div class="ilgs-feature-group">
            <div class="ilgs-section-title">Persons</div>
            ${personCards || '<div class="ilgs-feature-item"><div class="ilgs-feature-meta">No persons extracted.</div></div>'}
          </div>

          <div class="ilgs-feature-group">
            <div class="ilgs-section-title">Terms</div>
            ${termCards || '<div class="ilgs-feature-item"><div class="ilgs-feature-meta">No terms extracted.</div></div>'}
          </div>

          <div class="ilgs-feature-group">
            <div class="ilgs-section-title">Locations</div>
            ${locationCards || '<div class="ilgs-feature-item"><div class="ilgs-feature-meta">No locations extracted.</div></div>'}
          </div>

          <div class="ilgs-feature-group">
            <div class="ilgs-section-title">Dates</div>
            ${dateCards || '<div class="ilgs-feature-item"><div class="ilgs-feature-meta">No dates extracted.</div></div>'}
          </div>

          <div class="ilgs-feature-group">
            <div class="ilgs-section-title">External documents</div>
            ${extDocCards || '<div class="ilgs-feature-item"><div class="ilgs-feature-meta">No external documents extracted.</div></div>'}
          </div>

          <div class="ilgs-feature-group">
            <div class="ilgs-section-title">Quotes</div>
            ${quoteCards || '<div class="ilgs-feature-item"><div class="ilgs-feature-meta">No quotes extracted.</div></div>'}
          </div>
        `;
      }

      function addAnn(annotations, span, cls, title, extra) {
        if (!span || span.start == null || span.end == null) return;
        annotations.push(Object.assign({ start: span.start, end: span.end, cls, title }, extra || {}));
      }

      function renderAnnotatedDocument(doc) {
        const text = String(doc.text || "");
        const map = cpToCuMap(text);

        const annotations = [];
        const anchorsByStart = new Map();

        const segments = Array.isArray(doc.segments) ? doc.segments : [];
        const segById = new Map();
        segments.forEach(seg => {
          segById.set(seg.id, seg);
          if (seg.span && seg.span.start != null) {
            if (!anchorsByStart.has(seg.span.start)) anchorsByStart.set(seg.span.start, []);
            anchorsByStart.get(seg.span.start).push(seg.id);
          }
        });

        (doc.persons || []).forEach(p => {
          (p.mentions || []).forEach(sp => addAnn(annotations, sp, "person", spanText(text, map, p.name) || p.id));
        });
        (doc.terms || []).forEach(t => {
          addAnn(annotations, t.name, "term", spanText(text, map, t.name) || t.id);
          (t.mentions || []).forEach(sp => addAnn(annotations, sp, "term", spanText(text, map, t.name) || t.id));
        });
        (doc.locations || []).forEach(l => addAnn(annotations, l.name, "location", spanText(text, map, l.name) || l.id));
        (doc.dates || []).forEach(d => {
          const sp = d.span || d.value_span || d.date || null;
          addAnn(annotations, sp, "date", d.value || d.type || "date");
        });
        (doc.quotes || []).forEach(q => {
          const sp = q.span || q.quote || q.content || null;
          addAnn(annotations, sp, "quote", "Quote");
        });
        (doc.crossreferences || []).forEach((x, idx) => {
          addAnn(annotations, x.span, "xref", `Cross-reference ${idx + 1}`, {
            targetStart: x.start || "",
            targetEnd: x.end || ""
          });
        });

        const starts = new Map();
        const ends = new Map();
        const boundaries = new Set([0, [...text].length]);

        annotations.forEach((ann, idx) => {
          ann._id = `ann_${idx}`;
          if (!starts.has(ann.start)) starts.set(ann.start, []);
          if (!ends.has(ann.end)) ends.set(ann.end, []);
          starts.get(ann.start).push(ann);
          ends.get(ann.end).push(ann);
          boundaries.add(ann.start);
          boundaries.add(ann.end);
        });
        for (const pos of anchorsByStart.keys()) boundaries.add(pos);

        const sortedBounds = Array.from(boundaries).sort((a, b) => a - b);

        let out = '';
        let prev = 0;

        function openTag(ann) {
          const attrs = [
            `class="ilgs-ann ${ann.cls}"`,
            ann.title ? `title="${esc(ann.title)}"` : ""
          ];
          if (ann.cls === "xref") {
            attrs.push(`data-target-start="${esc(ann.targetStart || "")}"`);
            attrs.push(`data-target-end="${esc(ann.targetEnd || "")}"`);
          }
          return `<span ${attrs.filter(Boolean).join(" ")}>`;
        }

        function closeTag() { return `</span>`; }

        sortedBounds.forEach(pos => {
          if (prev < pos) {
            out += esc(sliceCp(text, map, prev, pos));
          }

          const ending = (ends.get(pos) || []).slice().sort((a, b) => b.start - a.start);
          ending.forEach(() => { out += closeTag(); });

          const anchors = anchorsByStart.get(pos) || [];
          anchors.forEach(segId => {
            out += `<span class="ilgs-anchor" id="seg-anchor-${esc(segId)}"></span>`;
          });

          const starting = (starts.get(pos) || []).slice().sort((a, b) => b.end - a.end);
          starting.forEach(ann => { out += openTag(ann); });

          prev = pos;
        });

        const hierarchyHtml = buildSegmentTree(doc, text, map);
        const featureHtml = buildFeaturePanel({}, doc, text, map);

        return `
          <div class="ilgs-layout">
            <div class="ilgs-panel ilgs-left">
              <div class="ilgs-section-title">Hierarchy</div>
              ${hierarchyHtml || '<div class="ilgs-feature-meta">No segment hierarchy available.</div>'}
            </div>

            <div class="ilgs-panel ilgs-center">
              <div class="ilgs-doc-toolbar">
                <div class="ilgs-section-title" style="margin:0;">Document view</div>
                <div class="ilgs-legend">
                  <span class="ilgs-legend-item"><span class="ilgs-ann person">&nbsp;&nbsp;&nbsp;</span> Person</span>
                  <span class="ilgs-legend-item"><span class="ilgs-ann term">&nbsp;&nbsp;&nbsp;</span> Term</span>
                  <span class="ilgs-legend-item"><span class="ilgs-ann location">&nbsp;&nbsp;&nbsp;</span> Location</span>
                  <span class="ilgs-legend-item"><span class="ilgs-ann date">&nbsp;&nbsp;&nbsp;</span> Date</span>
                  <span class="ilgs-legend-item"><span class="ilgs-ann xref">&nbsp;&nbsp;&nbsp;</span> Cross-reference</span>
                </div>
              </div>
              <div class="ilgs-doc" id="ilgs-doc-scroll">
                ${out}
              </div>
            </div>

            <div class="ilgs-panel ilgs-right">
              ${featureHtml}
            </div>
          </div>
        `;
      }

      function openPreview(rowIndex) {
        const record = records[rowIndex];
        const title = record.pretty_title || record.title || record.source_name || "Untitled";
        const doc = record.enriched_doc;

        if (doc && doc.text) {
          openModal(title, renderAnnotatedDocument(doc), false);
          setTimeout(() => {
            modalBody.querySelectorAll(".ilgs-tree-btn[data-seg-id]").forEach(btn => {
              btn.onclick = () => {
                const segId = btn.getAttribute("data-seg-id");
                const anchor = modalBody.querySelector(`#seg-anchor-${CSS.escape(segId)}`);
                if (anchor) anchor.scrollIntoView({ behavior: "smooth", block: "start" });
              };
            });
            modalBody.querySelectorAll(".ilgs-ann.xref").forEach(el => {
              el.onclick = () => {
                const targetStart = el.getAttribute("data-target-start");
                if (!targetStart) return;
                const anchor = modalBody.querySelector(`#seg-anchor-${CSS.escape(targetStart)}`);
                if (anchor) anchor.scrollIntoView({ behavior: "smooth", block: "start" });
              };
            });
          }, 0);
          return;
        }

        if (record._text_excerpt) {
          openModal(title, `<div class="mv-card"><div class="mv-card-title">Preview excerpt</div><div class="mv-card-text">${esc(record._text_excerpt)}</div></div>`, true);
          return;
        }

        openModal(title, `<div class="mv-card"><div class="mv-card-text">No enriched document is available for preview.</div></div>`, true);
      }

      function openParties(rowIndex) {
        const record = records[rowIndex];
        const parties = record.parties || [];
        const title = `Parties — ${record.pretty_title || record.title || record.source_name || "Untitled"}`;
        if (!parties.length) {
          openModal(title, `<div class="mv-card"><div class="mv-card-text">No parties extracted.</div></div>`, true);
          return;
        }

        const cards = parties.map((party) => {
          if (typeof party === "string") {
            return `
              <div class="mv-party-card">
                <div class="mv-party-head">
                  <div class="mv-party-name">${esc(party)}</div>
                </div>
              </div>
            `;
          }

          const name = party.name || "Unnamed party";
          const role = party.role || "Unknown role";
          const residence = party.residence || "";
          return `
            <div class="mv-party-card">
              <div class="mv-party-head">
                <div class="mv-party-name">${esc(name)}</div>
                ${rolePill(role)}
              </div>
              ${residence ? `<div class="mv-party-meta">Residence: ${esc(residence)}</div>` : ""}
            </div>
          `;
        }).join("");

        openModal(title, cards, true);
      }

      function openList(rowIndex, field, titleLabel) {
        const record = records[rowIndex];
        const title = `${titleLabel} — ${record.pretty_title || record.title || record.source_name || "Untitled"}`;
        const values = record[field] || [];
        if (!values.length) {
          openModal(title, `<div class="mv-card"><div class="mv-card-text">No data extracted.</div></div>`, true);
          return;
        }

        if (field === "locations") {
          const items = values.map((loc) =>
            `<button type="button" data-location="${esc(loc)}">${esc(loc)}</button>`
          ).join("");
          openModal(title, `
            <div class="mv-map-layout">
              <div class="mv-location-list">${items}</div>
              <iframe id="mv-map-frame" class="mv-map-frame"></iframe>
            </div>
          `, false);
          const frame = modalBody.querySelector("#mv-map-frame");
          const buttons = [...modalBody.querySelectorAll("button[data-location]")];
          function setLocation(loc) {
            frame.src = "https://www.google.com/maps?q=" + encodeURIComponent(loc) + "&output=embed";
          }
          buttons.forEach((btn, idx) => {
            btn.onclick = () => setLocation(btn.getAttribute("data-location"));
            if (idx === 0) setLocation(btn.getAttribute("data-location"));
          });
          return;
        }

        if (field === "terms") {
          const cards = values.map(v =>
            `<div class="mv-card"><div class="mv-card-title">${esc(v.name || "Unnamed term")}</div><div class="mv-card-text">${esc(v.definition || "No definition extracted.")}</div></div>`
          ).join("");
          openModal(title, cards, true);
          return;
        }

        const cards = values.map(v =>
          `<div class="mv-card"><div class="mv-card-text">${esc(typeof v === "string" ? v : JSON.stringify(v, null, 2))}</div></div>`
        ).join("");
        openModal(title, cards, true);
      }

      function exportJson() {
        const blob = new Blob([JSON.stringify(records, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "metadata_records.json";
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 500);
      }

      root.addEventListener("click", (event) => {
        const target = event.target.closest("[data-action]");
        if (!target) return;
        const rowIndex = Number(target.getAttribute("data-row"));
        const action = target.getAttribute("data-action");
        if (action === "preview") openPreview(rowIndex);
        if (action === "parties") openParties(rowIndex);
        if (action === "locations") openList(rowIndex, "locations", "Locations");
        if (action === "terms") openList(rowIndex, "terms", "Terms");
        if (action === "signatures") openList(rowIndex, "signatures", "Signatures");
      });

      closeBtn.onclick = closeModal;
      overlay.addEventListener("click", (event) => {
        if (event.target === overlay) closeModal();
      });
      exportBtn.onclick = exportJson;
    })();
  </script>
</div>
"""


def build_viewer_html(records: list[dict[str, Any]], category_options: list[str] | None = None) -> str:
    safe_records = [_record_for_json(r) for r in records]
    root_id = "mv-" + uuid.uuid4().hex
    data_id = root_id + "-data"
    overlay_id = root_id + "-overlay"
    title_id = root_id + "-title"
    body_id = root_id + "-body"
    close_id = root_id + "-close"
    export_id = root_id + "-export"

    count_label = f"{len(safe_records)} document" + ("" if len(safe_records) == 1 else "s")
    content = (
        HTML_TEMPLATE
        .replace("__ROOT_ID__", root_id)
        .replace("__DATA_ID__", data_id)
        .replace("__OVERLAY_ID__", overlay_id)
        .replace("__TITLE_ID__", title_id)
        .replace("__BODY_ID__", body_id)
        .replace("__CLOSE_ID__", close_id)
        .replace("__EXPORT_ID__", export_id)
        .replace("__COUNT_LABEL__", count_label)
        .replace("__ROWS_HTML__", _build_rows_html(safe_records))
        .replace("__DATA_JSON__", json.dumps(safe_records).replace("</", "<\\\\/"))
    )
    return content


def render_viewer(
    records: list[dict[str, Any]],
    category_options: list[str] | None = None,
    *,
    status: Any = None,
    stage_label: Any = None,
    viewer_out: Any = None,
    log: Optional[Callable[..., Any]] = None,
) -> str:
    html_out = build_viewer_html(records, category_options)

    if status is not None:
        status.value = "<b>Status:</b> Rendering viewer…"

    if viewer_out is not None:
        with viewer_out:
            clear_output(wait=True)
            display(HTML(html_out))

    if status is not None:
        status.value = f"<b>Status:</b> Ready · {len(records)} document(s)"

    if stage_label is not None:
        stage_label.value = "<b>Stage:</b> Idle"

    if log is not None:
        log("[render] completed")

    return html_out
