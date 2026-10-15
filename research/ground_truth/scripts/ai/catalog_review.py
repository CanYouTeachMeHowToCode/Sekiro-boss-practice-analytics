"""A local page for reviewing a ground-truth sheet with the mouse: ✅ / ❌ buttons and a reason box per row.

Usage: python -I catalog_review.py [port] [sheet]        (default port 8765, sheet "catalog")

Sheets:
    catalog          semantic/genichiro_catalog.md and .csv (the move catalog, plan step 5)
    classification   semantic/genichiro_classification.md and engine/genichiro_castle_tae_classes.csv (every TAE
                     entry, plan step 7); the page can also filter by confidence
    decisions        semantic/genichiro_product_decisions.md and .csv (catalog → product moves, plan step 8); the page
                     can also filter by strength of evidence, and has a name box (招式名称) on every row whose
                     Chinese name has no wiki source

Then open http://127.0.0.1:<port> — in VS Code: Command Palette → "Simple Browser: Show".
Every click is written straight into the sheet's .md (the 审核 and 理由 cells of that row, and the review counts when
the sheet has them) and into the owner_review / owner_reason columns of its .csv, exactly as if the cells had been
edited by hand. The files are re-read on every request, so hand edits made meanwhile are kept.
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
MARKS = {"☐": "待审核", "✅": "通过", "❌": "不通过"}
CLASS_ZH = {"mapped_to_semantic_move": "属于招式", "duplicate_or_shared": "被借用的源动画", "unused_or_unreachable": "天守阁 AI 不会出",
            "non_combat": "非招式(格挡、弹刀、侧步、待机)", "hit_reaction": "受击和反应", "locomotion": "移动",
            "cinematic_or_scripted": "忍杀、死亡和演出", "unknown": "unknown"}


def catalog_view(r):
    fam = " / ".join(x for x in (r["family_proposed"], r["variant_proposed"]) if x)
    if r["family_proposed"].startswith("飞渡浮舟") and r["kind"] == "move":
        group = (0, "飞渡浮舟一族")
    elif r["kind"] == "move":
        group = (1, "其他招式候选:一、二阶段(c7100)") if r["character"] == "c7100" else (2, "其他招式候选:三阶段(c7110)")
    else:
        group = (3, "不算招式(建议)")
    fields = [("触发", r["trigger"]), ("攻击(击数)", r["attack_anims"]), ("飞行物", r["bullet_anims"]),
              ("其他动画", r["other_anims"] if r["kind"] == "not_move" else ""), ("录到次数", r["recorded"]),
              ("最早录到", r["first_seen"]),
              ("建议的招式族", fam + (f"(依据:{r['family_basis']})" if r["family_basis"] else "") if fam else ""),
              ("wiki 候选", r["wiki_candidate"] + (f"(依据:{r['wiki_basis']})" if r["wiki_basis"] else "")),
              ("你的标注", r["owner_labels"]), ("共用动画", r["shares_animations_with"]), ("说明", r["notes"]),
              ("AI 选项", r["ai_options"])]
    return {"title": r["entry"], "sub": f"阶段 {r['phases']}" + (f" · {r['evidence']}" if r["evidence"] else ""),
            "mono": r["chain"], "fields": [[k, v] for k, v in fields if v], "group": group, "tag": ""}


def classification_view(r):
    order = list(CLASS_ZH).index(r["class"]) if r["class"] in CLASS_ZH else 99
    fields = [("依据", r["basis"]), ("备注", r["note"]), ("TAE 类别", r["tae_category"]), ("天守阁 AI", r["castle_ai"]),
              ("两次录像出现", r["recorded"]), ("目录条目", r["catalog_entries"])]
    return {"title": r["key"], "sub": f"{CLASS_ZH.get(r['class'], r['class'])} · 置信度 {r['confidence']}", "mono": "",
            "fields": [[k, v] for k, v in fields if v], "group": (order, f"{CLASS_ZH.get(r['class'], r['class'])}(`{r['class']}`)"),
            "tag": r["confidence"]}


def decisions_view(r):
    if r["section"] == "A":
        title, group = f"{r['key']} {r['product_name_zh']}", (0, "A. 产品现有的招式")
        sub = f"`{r['product_slug']}` · 产品阶段 {r['phases']}" + (f" · 依据{r['strength']}" if r["strength"] else "")
    else:
        title, group = f"{r['key']} {r['catalog_entries']}", (1, "B. 目录里还没对上产品的招式")
        sub = f"阶段 {r['phases']} · {r['evidence']}"
    fields = [("建议", r["proposal"]), ("依据", r["basis"]), ("目录条目", r["catalog_entries"] if r["section"] == "A" else ""),
              ("动画", r["anims"]), ("两次录像出现", r["recorded"]), ("证据", r["evidence"] if r["section"] == "A" else ""),
              ("你的标注", r["owner_labels"]), ("wiki", r["wiki"]), ("英文名", r["product_name"]), ("触发", r["trigger"])]
    return {"title": title, "sub": sub, "mono": r["chains"], "fields": [[k, v] for k, v in fields if v], "group": group,
            "tag": r["strength"]}


SHEETS = {
    "catalog": {"md": GT / "semantic/genichiro_catalog.md", "csv": GT / "semantic/genichiro_catalog.csv", "key": "entry",
                "title": "天守阁弦一郎招式目录 · 审核", "view": catalog_view, "tags": []},
    "classification": {"md": GT / "semantic/genichiro_classification.md", "csv": GT / "engine/genichiro_castle_tae_classes.csv",
                       "key": "key", "title": "天守阁弦一郎 TAE 全集分类 · 审核", "view": classification_view,
                       "tags": ["高", "中", "低"]},
    "decisions": {"md": GT / "semantic/genichiro_product_decisions.md", "csv": GT / "semantic/genichiro_product_decisions.csv",
                  "key": "key", "title": "第 8 步决策表:招式目录 → 产品招式", "view": decisions_view,
                  "tags": ["强", "中", "弱"], "tag_label": "依据强弱",
                  "name": {"col": 4, "csv": "owner_name", "label": "招式名称", "editable": lambda r: r["name_source"] != "wiki",
                           "placeholder": lambda r: (f"留空 = 用现在的名字:{r['product_name_zh']} / {r['product_name']}"
                                                     if r["section"] == "A" else "中文名 / English name(新增时必填)")}},
}
SHEET = SHEETS[sys.argv[2] if len(sys.argv) > 2 else "catalog"]
MD, CSV, KEY = SHEET["md"], SHEET["csv"], SHEET["key"]
NAME = SHEET.get("name")     # an optional third editable cell (column NAME["col"] of the .md, NAME["csv"] of the .csv)


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
    keys = {r[KEY] for r in rows}
    marks = {}
    for line in read_lines(MD):
        parts = line.rstrip("\r\n").split("|")
        if len(parts) > 4 and parts[1].strip() in keys:
            name = parts[NAME["col"]].strip() if NAME and len(parts) > NAME["col"] + 1 else ""
            marks[parts[1].strip()] = (parts[2].strip() or "☐", parts[3].strip(), "" if name == "—" else name)
    for r in rows:
        r["mark"], r["reason"], r["name"] = marks.get(r[KEY], ("☐", "", ""))
    return rows


def status(mark):
    if "❌" in mark or "不通过" in mark:
        return "不通过"
    if "✅" in mark or "通过" in mark:
        return "通过"
    return "待审核"


def save(key, mark, reason, name=None):
    reason = " ".join(reason.replace("|", "｜").split())
    rows = load()
    if key not in {r[KEY] for r in rows}:
        raise ValueError(f"unknown row {key}")
    if name is not None:
        name = " ".join(name.replace("|", "｜").split())
        if not (NAME and NAME["editable"](next(r for r in rows if r[KEY] == key))):
            raise ValueError(f"row {key} has no name to fill")
    for r in rows:
        if r[KEY] == key:
            r["mark"], r["reason"] = mark, reason
    counts = {(c, s): 0 for c in ("c7100", "c7110") for s in MARKS.values()}
    for r in rows:
        counts[(r["character"], status(r["mark"]))] += 1
    out = []
    for line in read_lines(MD):
        end = line[len(line.rstrip("\r\n")):]
        parts = line.rstrip("\r\n").split("|")
        if len(parts) > 4 and parts[1].strip() == key:
            parts[2], parts[3] = f" {mark} ", f" {reason} "
            if name is not None:
                parts[NAME["col"]] = f" {name} "
            line = "|".join(parts) + end
        for m, s in MARKS.items():
            if line.startswith(f"| 审核 {m} {s} |"):
                line = f"| 审核 {m} {s} | {counts[('c7100', s)]} | {counts[('c7110', s)]} |" + end
        out.append(line)
    write_text(MD, "".join(out))
    table = list(csv.DictReader(open(CSV, encoding="utf-8")))
    for r in table:
        if r[KEY] == key:
            r["owner_review"], r["owner_reason"] = status(mark), reason
            if name is not None:
                r[NAME["csv"]] = name
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(table[0]), lineterminator="\r\n")
    w.writeheader()
    w.writerows(table)
    write_text(CSV, buf.getvalue())
    return {s: counts[("c7100", s)] + counts[("c7110", s)] for s in MARKS.values()}


def view_rows():
    out = []
    for r in load():
        v = SHEET["view"](r)
        v.update({"key": r[KEY], "mark": r["mark"], "reason": r["reason"], "name": r["name"], "name_field": None})
        if NAME and NAME["editable"](r):
            v["name_field"] = {"label": NAME["label"], "placeholder": NAME["placeholder"](r)}
        out.append(v)
    out.sort(key=lambda v: v["group"][0])   # stable: keeps the sheet's order inside each group
    for v in out:
        v["group"] = v["group"][1]
    return out


PAGE = r"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root { --bg:#fbfbfa; --panel:#fff; --fg:#1f1f1e; --muted:#6b6b66; --line:#e3e2de; --ok:#1f7a4d; --okbg:#e6f4ec; --bad:#b3261e; --badbg:#fbe9e7; --chip:#f1f0ec; }
@media (prefers-color-scheme: dark) { :root { --bg:#1e1e1e; --panel:#252526; --fg:#e6e6e3; --muted:#a3a39e; --line:#3a3a3a; --ok:#5cc58f; --okbg:#1f3a2b; --bad:#f28b82; --badbg:#3d2321; --chip:#2f2f2f; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:14px/1.5 system-ui, "Microsoft YaHei", sans-serif; }
header { position:sticky; top:0; z-index:2; background:var(--bg); border-bottom:1px solid var(--line); padding:10px 16px; display:flex; flex-wrap:wrap; gap:8px 16px; align-items:center; }
h1 { font-size:16px; margin:0; font-weight:600; }
.counts span { margin-right:12px; font-variant-numeric:tabular-nums; }
.filters { display:flex; gap:4px; flex-wrap:wrap; align-items:center; }
.filters .lab { color:var(--muted); font-size:12px; margin:0 2px 0 6px; }
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
.review { display:flex; flex-direction:column; gap:6px; }
.btns { display:flex; gap:6px; }
.btns button { flex:1; font:inherit; font-size:15px; padding:6px 0; border-radius:6px; border:1px solid var(--line); background:var(--panel); color:var(--fg); cursor:pointer; }
.btns button.on.ok { background:var(--okbg); border-color:var(--ok); color:var(--ok); font-weight:600; }
.btns button.on.bad { background:var(--badbg); border-color:var(--bad); color:var(--bad); font-weight:600; }
.btns button.reset { flex:0 0 40px; color:var(--muted); }
.namebox label { display:block; font-size:12px; color:var(--muted); margin-bottom:2px; }
.namebox input { font:inherit; width:100%; border:1px solid var(--line); border-radius:6px; padding:5px 6px; background:var(--bg); color:var(--fg); }
textarea { font:inherit; width:100%; min-height:64px; resize:vertical; border:1px solid var(--line); border-radius:6px; padding:6px; background:var(--bg); color:var(--fg); }
.saved { font-size:12px; color:var(--muted); min-height:18px; }
.hint { color:var(--muted); font-size:13px; }
</style></head><body>
<header>
  <h1>__TITLE__</h1>
  <div class="counts" id="counts"></div>
  <div class="filters" id="filters"></div>
</header>
<main>
  <p class="hint">点 ✅ 或 ❌ 就会写进 <code>__MDNAME__</code>。不通过时在框里写理由,离开输入框或停顿一秒后自动保存。↺ 恢复成待审核。</p>
  <div id="list"></div>
</main>
<script id="data" type="application/json">__DATA__</script>
<script>
const rows = JSON.parse(document.getElementById('data').textContent);
const TAGS = __TAGS__;
const TAG_LABEL = __TAGLABEL__;
const FILTERS = ['全部', '待审核', '通过', '不通过'];
let filter = '待审核', tag = '全部';
const status = (m) => m.includes('❌') ? '不通过' : (m.includes('✅') ? '通过' : '待审核');
const el = (tagName, cls, text) => { const e = document.createElement(tagName); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; };

function counts() {
  const c = { '待审核': 0, '通过': 0, '不通过': 0 };
  rows.forEach((r) => c[status(r.mark)]++);
  document.getElementById('counts').replaceChildren(el('span', '', `✅ ${c['通过']}`), el('span', '', `❌ ${c['不通过']}`), el('span', '', `☐ ${c['待审核']} / ${rows.length}`));
}
function filters() {
  const box = document.getElementById('filters');
  const btn = (label, active, on) => { const b = el('button', '', label); b.setAttribute('aria-pressed', String(active)); b.onclick = on; return b; };
  const items = FILTERS.map((f) => btn(f, f === filter, () => { filter = f; render(); }));
  if (TAGS.length) {
    items.push(el('span', 'lab', TAG_LABEL));
    ['全部', ...TAGS].forEach((t) => items.push(btn(t, t === tag, () => { tag = t; render(); })));
  }
  box.replaceChildren(...items);
}
async function post(r, note) {
  note.textContent = '保存中…';
  try {
    const res = await fetch('/api/review', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key: r.key, mark: r.mark, reason: r.reason, name: r.name_field ? r.name : null }) });
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
  const head = el('div'); head.append(el('span', 'id', r.title), el('span', 'ph', r.sub));
  info.append(head);
  if (r.mono) info.append(el('div', 'chain', r.mono));
  const dl = el('dl');
  r.fields.forEach(([k, v]) => dl.append(el('dt', '', k), el('dd', '', v)));
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
  rv.append(btns);
  if (r.name_field) {
    const box = el('div', 'namebox'), inp = el('input');
    const lab = el('label', '', r.name_field.label);
    inp.placeholder = r.name_field.placeholder; inp.value = r.name;
    let tn = null;
    const saveName = () => { if (inp.value !== r.name) { r.name = inp.value; r.reason = ta.value; post(r, note); } };
    inp.oninput = () => { clearTimeout(tn); tn = setTimeout(saveName, 1000); };
    inp.onblur = () => { clearTimeout(tn); saveName(); };
    box.append(lab, inp);
    rv.append(box);
  }
  rv.append(ta, note);
  c.append(info, rv);
  return c;
}
function render() {
  counts(); filters();
  const shown = rows.filter((r) => (filter === '全部' || status(r.mark) === filter) && (tag === '全部' || r.tag === tag));
  const out = [];
  let group = null, n = 0;
  const groups = {};
  shown.forEach((r) => { groups[r.group] = (groups[r.group] || 0) + 1; });
  shown.forEach((r) => {
    if (r.group !== group) { group = r.group; out.push(el('h2', '', `${group}(${groups[group]})`)); }
    out.push(card(r)); n++;
  });
  if (!n) out.push(el('p', 'hint', '没有符合这个筛选的条目。'));
  document.getElementById('list').replaceChildren(...out);
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
        data = json.dumps(view_rows(), ensure_ascii=False).replace("</", "<\\/")
        page = (PAGE.replace("__TITLE__", SHEET["title"]).replace("__MDNAME__", str(MD.relative_to(GT)).replace("\\", "/"))
                .replace("__TAGS__", json.dumps(SHEET["tags"], ensure_ascii=False))
                .replace("__TAGLABEL__", json.dumps(SHEET.get("tag_label", "置信度"), ensure_ascii=False)).replace("__DATA__", data))
        self._send(200, page, "text/html; charset=utf-8")

    def do_POST(self):
        if self.path != "/api/review":
            return self._send(404, "not found", "text/plain; charset=utf-8")
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8"))
            mark = body.get("mark", "☐")
            if mark not in MARKS:
                raise ValueError(f"bad mark {mark}")
            name = body.get("name")
            counts = save(str(body["key"]), mark, str(body.get("reason", "")), None if name is None else str(name))
            self._send(200, json.dumps({"ok": True, "counts": counts}, ensure_ascii=False), "application/json")
        except Exception as ex:  # noqa: BLE001
            self._send(400, json.dumps({"ok": False, "error": str(ex)}, ensure_ascii=False), "application/json")

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"{SHEET['title']}: http://127.0.0.1:{port}  (VS Code: Ctrl+Shift+P → Simple Browser: Show)")
    print(f"写入 {MD.relative_to(GT.parent.parent)},按 Ctrl+C 停止")
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
