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
      --bg:#f7f9fc; --surface:#fff; --border:#e6ecf3; --text:#132033; --muted:#68768b;
      --blue:#255cff; --blue-soft:#eef4ff; --shadow:0 12px 34px rgba(15,23,42,0.08);
      --font-scale: 1.35;
      font-family:Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color:var(--text); width:100%; max-width:100%; position:relative; box-sizing:border-box;
      font-size:calc(14px * var(--font-scale));
      text-align:left;
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
    .mv-modal { width:min(980px,100%); max-height:90%; overflow:hidden; background:var(--surface); border:1px solid var(--border); border-radius:18px; box-shadow:0 24px 80px rgba(15,23,42,.18); display:flex; flex-direction:column; }
    .mv-modal-head { display:flex; justify-content:space-between; align-items:center; padding:18px 18px; border-bottom:1px solid var(--border); text-align:left; }
    .mv-modal-head h4 { margin:0; font-size:calc(17px * var(--font-scale)); font-weight:650; text-align:left; }
    .mv-modal-close { width:32px; height:32px; border:0; border-radius:999px; background:#f2f5fa; cursor:pointer; font-size:calc(20px * var(--font-scale)); }
    .mv-modal-body { padding:18px; overflow:auto; text-align:left; }

    .mv-card { border:1px solid var(--border); border-radius:14px; padding:15px; background:#fafcff; margin-bottom:12px; text-align:left; }
    .mv-card-title { font-size:calc(14px * var(--font-scale)); font-weight:650; margin-bottom:8px; text-align:left; }
    .mv-card-text { font-size:calc(14px * var(--font-scale)); line-height:1.65; color:#334156; white-space:pre-wrap; text-align:left; }
    .mv-doc-frame { width:100%; height:62vh; border:1px solid var(--border); border-radius:14px; background:#fafcff; }

    .mv-party-card { border:1px solid var(--border); border-radius:14px; padding:15px; background:#fafcff; margin-bottom:12px; text-align:left; }
    .mv-party-head { display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:8px; justify-content:flex-start; }
    .mv-party-name { font-size:calc(15px * var(--font-scale)); font-weight:650; color:var(--text); text-align:left; }
    .mv-role-pill { display:inline-flex; align-items:center; padding:5px 10px; border-radius:999px; font-size:calc(12px * var(--font-scale)); font-weight:700; border:1px solid transparent; }
    .mv-party-meta { font-size:calc(13px * var(--font-scale)); color:var(--muted); text-align:left; }

    .mv-map-layout { display:grid; grid-template-columns:260px 1fr; gap:14px; align-items:start; }
    .mv-location-list button {
      display:block; width:100%; text-align:left; border:0; background:#fafcff; padding:10px;
      border-radius:10px; margin-bottom:6px; cursor:pointer; font:inherit;
    }
    .mv-map-frame { width:100%; height:340px; border:1px solid var(--border); border-radius:14px; background:#fafcff; }

    @media (max-width: 900px) {
      .mv-table-wrap { min-height:520px; max-height:920px; }
      .mv-map-layout { grid-template-columns:1fr; }
      .mv-map-frame { height:300px; }
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

      function openModal(title, bodyHtml) {
        modalTitle.textContent = title;
        modalBody.innerHTML = bodyHtml;
        overlay.classList.add("open");
      }

      function closeModal() {
        overlay.classList.remove("open");
      }

      function openPreview(rowIndex) {
        const record = records[rowIndex];
        const title = record.pretty_title || record.title || record.source_name || "Untitled";

        if (record._preview_base64 && record._mime_type === "application/pdf") {
          const dataUrl = `data:${record._mime_type};base64,${record._preview_base64}`;
          openModal(title, `
            <embed class="mv-doc-frame" src="${dataUrl}" type="application/pdf" />
            <div class="mv-card" style="margin-top:12px;">
              <div class="mv-card-text">If the PDF still does not appear, the browser or notebook may be blocking embedded PDF data URLs. In that case, keep the larger preview threshold in your notebook helper and rely on text excerpt fallback.</div>
            </div>
          `);
          return;
        }

        if (record._text_excerpt) {
          openModal(title, `<div class="mv-card"><div class="mv-card-title">Preview excerpt</div><div class="mv-card-text">${esc(record._text_excerpt)}</div></div>`);
          return;
        }

        openModal(title, `<div class="mv-card"><div class="mv-card-text">Preview unavailable. If this is a PDF, make sure your notebook is embedding a PDF preview payload for this file.</div></div>`);
      }

      function openParties(rowIndex) {
        const record = records[rowIndex];
        const parties = record.parties || [];
        const title = `Parties — ${record.pretty_title || record.title || record.source_name || "Untitled"}`;
        if (!parties.length) {
          openModal(title, `<div class="mv-card"><div class="mv-card-text">No parties extracted.</div></div>`);
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

        openModal(title, cards);
      }

      function openList(rowIndex, field, titleLabel) {
        const record = records[rowIndex];
        const title = `${titleLabel} — ${record.pretty_title || record.title || record.source_name || "Untitled"}`;
        const values = record[field] || [];
        if (!values.length) {
          openModal(title, `<div class="mv-card"><div class="mv-card-text">No data extracted.</div></div>`);
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
          `);
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
          openModal(title, cards);
          return;
        }

        const cards = values.map(v =>
          `<div class="mv-card"><div class="mv-card-text">${esc(typeof v === "string" ? v : JSON.stringify(v, null, 2))}</div></div>`
        ).join("");
        openModal(title, cards);
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
    root_id = "mv-" + uuid.uuid4().hex
    data_id = root_id + "-data"
    overlay_id = root_id + "-overlay"
    title_id = root_id + "-title"
    body_id = root_id + "-body"
    close_id = root_id + "-close"
    export_id = root_id + "-export"

    count_label = f"{len(records)} document" + ("" if len(records) == 1 else "s")
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
        .replace("__ROWS_HTML__", _build_rows_html(records))
        .replace("__DATA_JSON__", json.dumps(records).replace("</", "<\\\\/"))
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
