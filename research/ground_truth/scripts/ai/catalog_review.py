"""A local page for reviewing the move catalog with the mouse: ✅ / ❌ buttons and a reason box per entry.

Usage: python -I catalog_review.py [port]        (default port 8765)

Then open http://127.0.0.1:<port> — in VS Code: Command Palette → "Simple Browser: Show".
Every click is written straight into semantic/genichiro_catalog.md (the 审核 and 理由 cells of that entry, and the
review counts) and into the owner_review / owner_reason columns of semantic/genichiro_catalog.csv, exactly as if the
cells had been edited by hand. The files are re-read on every request, so hand edits made meanwhile are kept.
Only the Python standard library is used; the server listens on 127.0.0.1 only.
"""
import csv
import io
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

GT = Path(__file__).resolve().parent.parent.parent
MD = GT / "semantic/genichiro_catalog.md"
CSV = GT / "semantic/genichiro_catalog.csv"
MARKS = {"☐": "待审核", "✅": "通过", "❌": "不通过"}


def read_lines(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read().splitlines(keepends=True)


def write_text(path, text):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    os.replace(tmp, path)


def load():
    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    marks = {}
    for line in read_lines(MD):
        parts = line.rstrip("\r\n").split("|")
        if len(parts) > 4 and parts[1].strip() in {r["entry"] for r in rows}:
            marks[parts[1].strip()] = (parts[2].strip() or "☐", parts[3].strip())
    for r in rows:
        r["mark"], r["reason"] = marks.get(r["entry"], ("☐", ""))
    return rows


def status(mark):
    if "❌" in mark or "不通过" in mark:
        return "不通过"
    if "✅" in mark or "通过" in mark:
        return "通过"
    return "待审核"


def save(entry, mark, reason):
    reason = " ".join(reason.replace("|", "｜").split())
    rows = load()
    if entry not in {r["entry"] for r in rows}:
        raise ValueError(f"unknown entry {entry}")
    for r in rows:
        if r["entry"] == entry:
            r["mark"], r["reason"] = mark, reason
    counts = {(c, s): 0 for c in ("c7100", "c7110") for s in MARKS.values()}
    for r in rows:
        counts[(r["character"], status(r["mark"]))] += 1
    out = []
    for line in read_lines(MD):
        end = line[len(line.rstrip("\r\n")):]
        parts = line.rstrip("\r\n").split("|")
        if len(parts) > 4 and parts[1].strip() == entry:
            parts[2], parts[3] = f" {mark} ", f" {reason} "
            line = "|".join(parts) + end
        for m, s in MARKS.items():
            if line.startswith(f"| 审核 {m} {s} |"):
                line = f"| 审核 {m} {s} | {counts[('c7100', s)]} | {counts[('c7110', s)]} |" + end
        out.append(line)
    write_text(MD, "".join(out))
    table = list(csv.DictReader(open(CSV, encoding="utf-8")))
    for r in table:
        if r["entry"] == entry:
            r["owner_review"], r["owner_reason"] = status(mark), reason
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(table[0]), lineterminator="\r\n")
    w.writeheader()
    w.writerows(table)
    write_text(CSV, buf.getvalue())
    return {s: counts[("c7100", s)] + counts[("c7110", s)] for s in MARKS.values()}


PAGE = r"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>招式目录审核</title>
<style>
:root { --bg:#fbfbfa; --panel:#fff; --fg:#1f1f1e; --muted:#6b6b66; --line:#e3e2de; --ok:#1f7a4d; --okbg:#e6f4ec; --bad:#b3261e; --badbg:#fbe9e7; --chip:#f1f0ec; }
@media (prefers-color-scheme: dark) { :root { --bg:#1e1e1e; --panel:#252526; --fg:#e6e6e3; --muted:#a3a39e; --line:#3a3a3a; --ok:#5cc58f; --okbg:#1f3a2b; --bad:#f28b82; --badbg:#3d2321; --chip:#2f2f2f; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:14px/1.5 system-ui, "Microsoft YaHei", sans-serif; }
header { position:sticky; top:0; z-index:2; background:var(--bg); border-bottom:1px solid var(--line); padding:10px 16px; display:flex; flex-wrap:wrap; gap:8px 16px; align-items:center; }
h1 { font-size:16px; margin:0; font-weight:600; }
.counts span { margin-right:12px; font-variant-numeric:tabular-nums; }
.filters button { font:inherit; border:1px solid var(--line); background:var(--panel); color:var(--muted); border-radius:999px; padding:2px 12px; cursor:pointer; }
.filters button[aria-pressed=true] { background:var(--fg); color:var(--bg); border-color:var(--fg); }
main { padding:12px 16px 40px; max-width:1100px; }
h2 { font-size:15px; margin:22px 0 8px; }
.card { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:10px 12px; margin:8px 0; display:grid; grid-template-columns:minmax(0,1fr) 260px; gap:12px; }
.card.ok { border-left:4px solid var(--ok); } .card.bad { border-left:4px solid var(--bad); }
@media (max-width:760px) { .card { grid-template-columns:1fr; } }
.id { font-weight:600; font-variant-numeric:tabular-nums; } .ph { color:var(--muted); margin-left:6px; }
.chain { font-family:Consolas, monospace; font-size:13px; margin:4px 0; overflow-wrap:anywhere; }
dl { display:grid; grid-template-columns:max-content minmax(0,1fr); gap:2px 10px; margin:6px 0 0; font-size:13px; }
dt { color:var(--muted); } dd { margin:0; overflow-wrap:anywhere; }
.chip { display:inline-block; background:var(--chip); border-radius:4px; padding:0 6px; margin-right:4px; font-size:12px; }
.review { display:flex; flex-direction:column; gap:6px; }
.btns { display:flex; gap:6px; }
.btns button { flex:1; font:inherit; font-size:15px; padding:6px 0; border-radius:6px; border:1px solid var(--line); background:var(--panel); color:var(--fg); cursor:pointer; }
.btns button.on.ok { background:var(--okbg); border-color:var(--ok); color:var(--ok); font-weight:600; }
.btns button.on.bad { background:var(--badbg); border-color:var(--bad); color:var(--bad); font-weight:600; }
.btns button.reset { flex:0 0 40px; color:var(--muted); }
textarea { font:inherit; width:100%; min-height:64px; resize:vertical; border:1px solid var(--line); border-radius:6px; padding:6px; background:var(--bg); color:var(--fg); }
.saved { font-size:12px; color:var(--muted); min-height:18px; }
.hint { color:var(--muted); font-size:13px; }
</style></head><body>
<header>
  <h1>天守阁弦一郎招式目录 · 审核</h1>
  <div class="counts" id="counts"></div>
  <div class="filters" id="filters"></div>
</header>
<main>
  <p class="hint">点 ✅ 或 ❌ 就会写进 <code>semantic/genichiro_catalog.md</code>。不通过时在框里写理由,离开输入框或停顿一秒后自动保存。↺ 恢复成待审核。</p>
  <div id="list"></div>
</main>
<script id="data" type="application/json">__DATA__</script>
<script>
const rows = JSON.parse(document.getElementById('data').textContent);
const FILTERS = ['全部', '待审核', '通过', '不通过'];
let filter = '待审核';
const status = (m) => m.includes('❌') ? '不通过' : (m.includes('✅') ? '通过' : '待审核');
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; };

function counts() {
  const c = { '待审核': 0, '通过': 0, '不通过': 0 };
  rows.forEach((r) => c[status(r.mark)]++);
  const box = document.getElementById('counts');
  box.replaceChildren(el('span', '', `✅ ${c['通过']}`), el('span', '', `❌ ${c['不通过']}`), el('span', '', `☐ ${c['待审核']} / ${rows.length}`));
}
function filters() {
  const box = document.getElementById('filters');
  box.replaceChildren(...FILTERS.map((f) => { const b = el('button', '', f); b.setAttribute('aria-pressed', String(f === filter)); b.onclick = () => { filter = f; render(); }; return b; }));
}
async function post(r, note) {
  note.textContent = '保存中…';
  try {
    const res = await fetch('/api/review', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ entry: r.entry, mark: r.mark, reason: r.reason }) });
    const j = await res.json();
    note.textContent = j.ok ? '已保存' : ('保存失败:' + j.error);
  } catch (e) { note.textContent = '保存失败:服务没在运行?'; }
  counts();
}
function card(r) {
  const c = el('div', 'card');
  const st = status(r.mark);
  if (st === '通过') c.classList.add('ok'); if (st === '不通过') c.classList.add('bad');
  const info = el('div');
  const head = el('div'); head.append(el('span', 'id', r.entry), el('span', 'ph', `阶段 ${r.phases}` + (r.evidence ? ` · ${r.evidence}` : '')));
  info.append(head, el('div', 'chain', r.chain + (r.notes ? `(${r.notes})` : '')));
  const dl = el('dl');
  const add = (k, v) => { if (v) { dl.append(el('dt', '', k), el('dd', '', v)); } };
  add('触发', r.trigger);
  add('攻击(击数)', r.attack_anims); add('飞行物', r.bullet_anims); add('其他动画', r.kind === 'not_move' ? r.other_anims : '');
  add('录到次数', r.recorded); add('第一轮录像', r.first_seen);
  const fam = [r.family_proposed, r.variant_proposed].filter(Boolean).join(' / ');
  add('建议的招式族', fam ? fam + (r.family_basis ? `(依据:${r.family_basis})` : '') : '');
  add('wiki 候选', r.wiki_candidate ? r.wiki_candidate + (r.wiki_basis ? `(依据:${r.wiki_basis})` : '') : '');
  add('你的标注', r.owner_labels); add('共用动画', r.shares_animations_with); add('AI 选项', r.ai_options);
  info.append(dl);
  const rv = el('div', 'review');
  const btns = el('div', 'btns');
  const ok = el('button', 'ok', '✅ 通过'), bad = el('button', 'bad', '❌ 不通过'), reset = el('button', 'reset', '↺');
  reset.title = '恢复成待审核';
  if (st === '通过') ok.classList.add('on'); if (st === '不通过') bad.classList.add('on');
  const ta = el('textarea'); ta.placeholder = '理由(不通过时必填;部分同意也写在这里)'; ta.value = r.reason;
  const note = el('div', 'saved');
  const set = (m) => {
    // update this card in place (no re-render), so the reason box stays open after ❌
    r.mark = m; r.reason = ta.value; post(r, note);
    const s = status(m);
    c.classList.toggle('ok', s === '通过'); c.classList.toggle('bad', s === '不通过');
    ok.classList.toggle('on', s === '通过'); bad.classList.toggle('on', s === '不通过');
    if (s === '不通过' && !ta.value) ta.focus();
  };
  ok.onclick = () => set('✅'); bad.onclick = () => set('❌');
  reset.onclick = () => set('☐');
  let t = null;
  const saveReason = () => { if (ta.value !== r.reason) { r.reason = ta.value; post(r, note); } };
  ta.oninput = () => { clearTimeout(t); t = setTimeout(saveReason, 1000); };
  ta.onblur = () => { clearTimeout(t); saveReason(); };
  btns.append(ok, bad, reset);
  rv.append(btns, ta, note);
  c.append(info, rv);
  return c;
}
function render() {
  counts(); filters();
  const list = document.getElementById('list');
  const groups = [
    ['飞渡浮舟一族', (r) => r.kind === 'move' && r.family_proposed.startsWith('飞渡浮舟')],
    ['其他招式候选:一、二阶段(c7100)', (r) => r.kind === 'move' && r.character === 'c7100' && !r.family_proposed.startsWith('飞渡浮舟')],
    ['其他招式候选:三阶段(c7110)', (r) => r.kind === 'move' && r.character === 'c7110' && !r.family_proposed.startsWith('飞渡浮舟')],
    ['不算招式(建议)', (r) => r.kind === 'not_move'],
  ];
  const out = [];
  for (const [title, test] of groups) {
    const rs = rows.filter(test).filter((r) => filter === '全部' || status(r.mark) === filter);
    if (!rs.length) continue;
    out.push(el('h2', '', `${title}(${rs.length})`), ...rs.map(card));
  }
  if (!out.length) out.push(el('p', 'hint', '没有符合这个筛选的条目。'));
  list.replaceChildren(...out);
}
render();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path not in ("/", "/index.html"):
            return self._send(404, "not found", "text/plain; charset=utf-8")
        data = json.dumps(load(), ensure_ascii=False).replace("</", "<\\/")
        self._send(200, PAGE.replace("__DATA__", data), "text/html; charset=utf-8")

    def do_POST(self):
        if self.path != "/api/review":
            return self._send(404, "not found", "text/plain; charset=utf-8")
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8"))
            mark = body.get("mark", "☐")
            if mark not in MARKS:
                raise ValueError(f"bad mark {mark}")
            counts = save(str(body["entry"]), mark, str(body.get("reason", "")))
            self._send(200, json.dumps({"ok": True, "counts": counts}, ensure_ascii=False), "application/json")
        except Exception as ex:  # noqa: BLE001
            self._send(400, json.dumps({"ok": False, "error": str(ex)}, ensure_ascii=False), "application/json")

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"招式目录审核页面: http://127.0.0.1:{port}  (VS Code: Ctrl+Shift+P → Simple Browser: Show)")
    print(f"写入 {MD.relative_to(GT.parent.parent)},按 Ctrl+C 停止")
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
