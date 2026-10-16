"""A local page for checking the detected failure events with the mouse (standard library only, 127.0.0.1).

Usage: python -I review_events.py [port]          (default 8770; then open http://127.0.0.1:<port>)

For every recording in recordings.json that hud_pipeline.py has processed, the page lists the detected events
(damage, death, resurrection, posture break, Wolf's deathblow) with their thumbnail and a button that plays the
recording from two seconds before the event. The owner marks each one correct / wrong / unsure with a note, and adds the
events the detector missed (the video's current time can be used as the event time).

Reviews are written straight to research/ground_truth/annotations/<ruleset>/genichiro/<recording>/hud_events.csv:
key, type, time_s, verdict (correct / wrong / unsure / missed), note, updated. A detected event is matched to its
review by its key (type@time to 0.1 s), or failing that by type and a time within 0.3 s (1.0 s for posture breaks,
whose time moves with the detector rule), so reruns of the detector keep the reviews. An event the owner added as
missed that a later detector finds shows as confirmed, and editing it rewrites that row. The video is served with
HTTP range requests so the browser can seek.

The 招式 view lists, for the dev-menu recordings, the failures and the move behind each one as failure_answers.py
proposes them from the overlay. The owner marks each answer correct / wrong / unsure, picks the right product move when
it is wrong, and can add a note. Those reviews go to failure_moves.csv next to hud_events.csv: key (the failure's first
event), time_s, proposed (the move slug that was shown), verdict, correct_move, note, updated. A review whose proposed
move no longer matches the current proposal is shown as needing another look. The side panel counts the failures per
move, using the owner's correction where there is one.
"""
import csv
import io
import json
import os
import re
import sys
from datetime import datetime
from urllib.parse import unquote
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import GT, annotation_dir, recordings, video_path, work_dir  # noqa: E402

FIELDS = ["key", "type", "time_s", "verdict", "note", "updated"]
VERDICTS = {"correct", "wrong", "unsure", "missed", ""}
TYPES = {"damage", "death", "resurrection", "posture_break", "deathblow"}
MOVE_FIELDS = ["key", "time_s", "proposed", "verdict", "correct_move", "note", "updated"]
MOVE_VERDICTS = {"correct", "wrong", "unsure", ""}
OTHER_MOVE = "other"


def product_moves():
    rows = csv.DictReader(open(GT / "semantic/genichiro_product_moveset.csv", encoding="utf-8"))
    return [{"slug": r["slug"], "zh": r["name_zh"], "en": r["name_en"], "phases": r["phases"].split("、")} for r in rows]


def review_file(rec):
    return annotation_dir(rec) / "hud_events.csv"


def moves_file(rec):
    return annotation_dir(rec) / "failure_moves.csv"


def read_csv(path):
    return list(csv.DictReader(open(path, encoding="utf-8"))) if path.exists() else []


def write_csv(path, fields, rows):
    rows.sort(key=lambda r: float(r["time_s"]))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\r\n")
    w.writeheader()
    w.writerows(rows)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(buf.getvalue(), encoding="utf-8", newline="")
    os.replace(tmp, path)


def read_reviews(rec):
    return read_csv(review_file(rec))


def write_reviews(rec, rows):
    write_csv(review_file(rec), FIELDS, rows)


TOLERANCE = {"posture_break": 1.0}     # seconds; 0.3 for the other types


def match(review, event):
    if review["key"] == event["key"]:
        return True
    tolerance = TOLERANCE.get(event["type"], 0.3)
    return review["type"] == event["type"] and abs(float(review["time_s"]) - float(event["time_s"])) <= tolerance


def page_data():
    out = []
    for rec_id, rec in recordings().items():
        events_csv = work_dir(rec_id) / "events.csv"
        if not events_csv.exists():
            continue
        events = list(csv.DictReader(open(events_csv, encoding="utf-8")))
        reviews = read_reviews(rec)
        used = set()
        for e in events:
            r = next((r for i, r in enumerate(reviews) if i not in used and r["verdict"] != "missed" and match(r, e)), None)
            if r is not None:
                used.add(reviews.index(r))
            e["verdict"], e["review_note"] = (r["verdict"], r["note"]) if r else ("", "")
            e["review_key"] = r["key"] if r else e["key"]
            if r is None:
                # an event the owner added as missed, which the detector now finds: it is confirmed
                m = next((m for i, m in enumerate(reviews) if i not in used and m["verdict"] == "missed" and match(m, e)), None)
                if m is not None:
                    used.add(reviews.index(m))
                    e["verdict"], e["review_note"] = "correct", f"你补充过的漏检（{float(m['time_s']):.2f} 秒），现在已检测到"
                    e["review_key"] = m["key"]     # an edit replaces the missed row instead of adding a second one
        missed = [r for i, r in enumerate(reviews) if r["verdict"] == "missed" and i not in used]
        failures = read_csv(work_dir(rec_id) / "failure_answers.csv")
        done = {r["key"]: r for r in read_csv(moves_file(rec))}
        for f in failures:
            r = done.get(f["key"])
            f["verdict"], f["correct_move"], f["review_note"] = (r["verdict"], r["correct_move"], r["note"]) if r else ("", "", "")
            f["stale"] = bool(r and r["verdict"] and r["proposed"] != f["move"])
        out.append({"id": rec_id, "use": rec.get("use", ""), "overlay": rec.get("overlay", False), "events": events,
                    "missed": missed, "failures": failures})
    return {"recs": out, "moves": product_moves()}


def save(rec_id, body):
    rec = recordings()[rec_id]
    verdict, kind = body.get("verdict", ""), body["type"]
    if verdict not in VERDICTS or kind not in TYPES:
        raise ValueError("bad verdict or type")
    time_s = f"{float(body['time_s']):.3f}"
    key = body.get("key") or f"{kind}@{float(time_s):.1f}"
    note = " ".join(str(body.get("note", "")).split())
    rows = [r for r in read_reviews(rec) if r["key"] != key]
    if verdict or note:
        rows.append({"key": key, "type": kind, "time_s": time_s, "verdict": verdict, "note": note,
                     "updated": datetime.now().isoformat(timespec="seconds")})
    write_reviews(rec, rows)
    return key


def save_move(rec_id, body):
    rec = recordings()[rec_id]
    verdict, correct = body.get("verdict", ""), body.get("correct_move", "")
    if verdict not in MOVE_VERDICTS:
        raise ValueError("bad verdict")
    if correct and correct not in {m["slug"] for m in product_moves()} | {OTHER_MOVE}:
        raise ValueError("unknown move")
    key, note = body["key"], " ".join(str(body.get("note", "")).split())
    rows = [r for r in read_csv(moves_file(rec)) if r["key"] != key]
    if verdict or note or correct:
        rows.append({"key": key, "time_s": f"{float(body['time_s']):.3f}", "proposed": body.get("proposed", ""),
                     "verdict": verdict, "correct_move": correct, "note": note,
                     "updated": datetime.now().isoformat(timespec="seconds")})
    write_csv(moves_file(rec), MOVE_FIELDS, rows)
    return key


PAGE = r"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>失败事件核对</title>
<style>
:root { --bg:#fbfbfa; --panel:#fff; --fg:#1f1f1e; --muted:#6b6b66; --line:#e3e2de; --ok:#1f7a4d; --okbg:#e6f4ec; --bad:#b3261e; --badbg:#fbe9e7; --warn:#8a6100; --warnbg:#fdf3dc; --chip:#f1f0ec; }
@media (prefers-color-scheme: dark) { :root { --bg:#1e1e1e; --panel:#252526; --fg:#e6e6e3; --muted:#a3a39e; --line:#3a3a3a; --ok:#5cc58f; --okbg:#1f3a2b; --bad:#f28b82; --badbg:#3d2321; --warn:#e8c26a; --warnbg:#3a3220; --chip:#2f2f2f; } }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:14px/1.5 system-ui, "Microsoft YaHei", sans-serif; }
header { position:sticky; top:0; z-index:3; background:var(--bg); border-bottom:1px solid var(--line); padding:8px 16px; display:flex; flex-wrap:wrap; gap:8px 16px; align-items:center; }
h1 { font-size:16px; margin:0; }
.tabs button, .filters button { font:inherit; border:1px solid var(--line); background:var(--panel); color:var(--muted); border-radius:999px; padding:2px 12px; cursor:pointer; }
.tabs button[aria-pressed=true], .filters button[aria-pressed=true] { background:var(--fg); color:var(--bg); border-color:var(--fg); }
.counts span { margin-right:10px; font-variant-numeric:tabular-nums; }
.layout { display:grid; grid-template-columns:minmax(0,1fr) 560px; gap:16px; padding:12px 16px 40px; }
@media (max-width:1100px) { .layout { grid-template-columns:1fr; } .player { position:static !important; } }
.player { position:sticky; top:56px; align-self:start; background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:10px; }
.player video { width:100%; border-radius:4px; background:#000; }
.player .now { font-variant-numeric:tabular-nums; color:var(--muted); margin:6px 0; }
.player form { display:grid; grid-template-columns:auto 1fr; gap:6px 8px; align-items:center; margin-top:8px; }
.player input, .player select, textarea { font:inherit; border:1px solid var(--line); border-radius:6px; padding:4px 6px; background:var(--bg); color:var(--fg); }
.card { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:10px 12px; margin:0 0 10px; }
.card.correct { border-left:4px solid var(--ok); } .card.wrong { border-left:4px solid var(--bad); } .card.unsure { border-left:4px solid var(--warn); }
.head { display:flex; flex-wrap:wrap; gap:6px 12px; align-items:baseline; margin-bottom:6px; }
.type { font-weight:600; } .time { font-variant-numeric:tabular-nums; }
.meta { color:var(--muted); font-size:13px; }
.card img { width:100%; border-radius:4px; cursor:zoom-in; display:block; }
.card img.big { cursor:zoom-out; }
.actions { display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; align-items:center; }
.actions button { font:inherit; padding:4px 12px; border-radius:6px; border:1px solid var(--line); background:var(--panel); color:var(--fg); cursor:pointer; }
.actions button.on.correct { background:var(--okbg); border-color:var(--ok); color:var(--ok); font-weight:600; }
.actions button.on.wrong { background:var(--badbg); border-color:var(--bad); color:var(--bad); font-weight:600; }
.actions button.on.unsure { background:var(--warnbg); border-color:var(--warn); color:var(--warn); font-weight:600; }
.actions textarea { flex:1 1 260px; min-height:34px; resize:vertical; }
.saved { font-size:12px; color:var(--muted); }
.hint { color:var(--muted); font-size:13px; margin:0 0 10px; }
.missed li { margin:4px 0; }
.answer { margin:2px 0 6px; } .answer strong { font-size:15px; }
ul.hits { margin:4px 0 8px; padding-left:18px; font-size:13px; }
.warnline { color:var(--warn); font-size:13px; margin:2px 0; }
.actions select { font:inherit; border:1px solid var(--line); border-radius:6px; padding:4px 6px; background:var(--bg); color:var(--fg); max-width:100%; }
.summary { margin-top:10px; font-size:13px; } .summary table { border-collapse:collapse; width:100%; }
.summary th, .summary td { text-align:left; padding:3px 6px; border-bottom:1px solid var(--line); font-variant-numeric:tabular-nums; }
.summary td.n, .summary th.n { text-align:right; }
</style></head><body>
<header>
  <h1>失败事件核对</h1>
  <div class="tabs" id="modes"></div>
  <div class="tabs" id="tabs"></div>
  <div class="filters" id="filters"></div>
  <div class="counts" id="counts"></div>
</header>
<div class="layout">
  <main>
    <p class="hint" id="hint"></p>
    <div id="list"></div>
  </main>
  <aside class="player">
    <video id="video" controls preload="metadata"></video>
    <div class="now" id="now"></div>
    <form id="addform">
      <label>漏掉的事件</label>
      <select id="addtype"><option value="damage">扣血</option><option value="posture_break">被打崩</option><option value="death">死亡</option><option value="deathblow">狼的忍杀</option></select>
      <label>时间（秒）</label>
      <span><input id="addtime" type="number" step="0.1" min="0" style="width:110px"> <button type="button" id="usenow">用录像当前时间</button></span>
      <label>备注</label><input id="addnote">
      <span></span><button type="submit">添加</button>
    </form>
    <ul class="missed" id="missed"></ul>
    <div class="summary" id="summary"></div>
  </aside>
</div>
<script id="data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
const recs = DATA.recs, MOVES = DATA.moves;
const MOVE = Object.fromEntries(MOVES.map((m) => [m.slug, m]));
const TYPE = { damage: '扣血', death: '死亡', resurrection: '回生（不算失败）', posture_break: '被打崩', deathblow: '狼的忍杀（不算失败）' };
const VERDICT = { correct: '✅ 对', wrong: '❌ 不对', unsure: '？不确定' };
const HINT = {
  events: '每个事件：看图或点"▶ 播放"从事件前 2 秒开始看录像，然后标 ✅ 对 / ❌ 不对 / ？不确定，可以写备注。点图片放大。回生和忍杀不算失败，只是方便你看清发生了什么。漏掉的事件在右边补上。',
  moves: '每次失败：答案是开发者菜单上被打中那一刻弦一郎在放的动画，按你批过的 AI 链和产品招式表对出来的。同一招连续几下、打崩和硬直中的追击、死亡和打死你的那一下已经按你的规则合并。看对不对，标 ✅ / ❌ / ？；不对时在下拉框里选正确的招式。点"▶ 播放"从失败前 3 秒开始看。',
};
let cur = 0, filter = '全部', mode = 'events';
const el = (t, c, x) => { const e = document.createElement(t); if (c) e.className = c; if (x !== undefined) e.textContent = x; return e; };
const fmt = (s) => { s = Number(s); const m = Math.floor(s / 60); return `${m}:${(s - m * 60).toFixed(1).padStart(4, '0')}`; };
const video = document.getElementById('video');
video.addEventListener('timeupdate', () => { document.getElementById('now').textContent = `录像当前时间 ${fmt(video.currentTime)}（${video.currentTime.toFixed(2)} 秒）`; });

async function post(body, url = '/api/review') {
  const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const j = await res.json();
  if (!j.ok) throw new Error(j.error);
  return j.key;
}
function counts() {
  const r = recs[cur], c = { '': 0, correct: 0, wrong: 0, unsure: 0 };
  const items = mode === 'moves' ? r.failures : r.events;
  items.forEach((e) => { c[e.verdict] = (c[e.verdict] || 0) + 1; });
  const parts = [el('span', '', `待核对 ${c['']}`), el('span', '', `✅ ${c.correct}`), el('span', '', `❌ ${c.wrong}`), el('span', '', `？ ${c.unsure}`)];
  if (mode === 'events') parts.push(el('span', '', `补充 ${r.missed.length}`));
  document.getElementById('counts').replaceChildren(...parts);
  if (mode === 'moves') summary();
}
function tabs() {
  document.getElementById('modes').replaceChildren(...[['events', '事件'], ['moves', '招式']].map(([m, label]) => {
    const b = el('button', '', label); b.setAttribute('aria-pressed', String(m === mode));
    b.onclick = () => { mode = m; filter = '全部'; render(false); }; return b;
  }));
  const shownRecs = recs.map((r, i) => [r, i]).filter(([r]) => mode === 'events' || r.failures.length);
  document.getElementById('tabs').replaceChildren(...shownRecs.map(([r, i]) => { const b = el('button', '', r.id); b.setAttribute('aria-pressed', String(i === cur)); b.onclick = () => { cur = i; render(true); }; return b; }));
  const f = mode === 'moves' ? ['全部', '待核对', '扣血', '被打崩', '死亡', '有提示'] : ['全部', '待核对', '扣血', '被打崩', '死亡', '忍杀'];
  document.getElementById('filters').replaceChildren(...f.map((x) => { const b = el('button', '', x); b.setAttribute('aria-pressed', String(x === filter)); b.onclick = () => { filter = x; render(false); }; return b; }));
}
function card(r, e) {
  const c = el('div', 'card ' + (e.verdict || ''));
  const head = el('div', 'head');
  head.append(el('span', 'type', TYPE[e.type] || e.type), el('span', 'time', fmt(e.time_s)));
  const hp = e.type === 'posture_break' ? `躯干清空；当时血量 ${e.hp_before}`
    : e.type === 'deathblow' ? `Boss 血量清空；狼的血量 ${e.hp_before}` : `血量 ${e.hp_before} → ${e.hp_after}`;
  head.append(el('span', 'meta', hp + (e.linked ? `；由 ${e.linked} 造成` : '') + (e.note ? `；${e.note}` : '')));
  const play = el('button', '', '▶ 播放'); play.type = 'button';
  play.onclick = () => { video.currentTime = Math.max(0, Number(e.time_s) - 2); video.play(); };
  head.append(play);
  c.append(head);
  const img = el('img'); img.loading = 'lazy'; img.src = `/thumb/${encodeURIComponent(r.id)}/${encodeURIComponent(e.key)}.jpg`;
  img.onclick = () => img.classList.toggle('big');
  c.append(img);
  const acts = el('div', 'actions'), note = el('div', 'saved');
  const ta = el('textarea'); ta.placeholder = '备注（可选）'; ta.value = e.review_note || '';
  const set = async (v) => {
    e.verdict = v; note.textContent = '保存中…';
    try { e.review_key = await post({ rec: r.id, key: e.review_key, type: e.type, time_s: e.time_s, verdict: v, note: ta.value }); note.textContent = '已保存'; }
    catch (err) { note.textContent = '保存失败：' + err.message; }
    c.className = 'card ' + (v || ''); [...acts.querySelectorAll('button[data-v]')].forEach((b) => b.classList.toggle('on', b.dataset.v === v)); counts();
  };
  for (const [v, label] of Object.entries(VERDICT)) {
    const b = el('button', v + (e.verdict === v ? ' on' : ''), label); b.type = 'button'; b.dataset.v = v; b.onclick = () => set(v); acts.append(b);
  }
  const reset = el('button', '', '↺'); reset.type = 'button'; reset.title = '恢复成待核对'; reset.onclick = () => { ta.value = ''; set(''); };
  acts.append(reset, ta, note);
  let timer = null;
  ta.oninput = () => { clearTimeout(timer); timer = setTimeout(() => set(e.verdict), 1000); };
  c.append(acts);
  return c;
}
function fcard(r, f) {
  const c = el('div', 'card ' + (f.verdict || ''));
  const head = el('div', 'head');
  head.append(el('span', 'type', TYPE[f.type] || f.type), el('span', 'time', fmt(f.time_s)), el('span', 'meta', `第 ${f.phase} 阶段`));
  const play = el('button', '', '▶ 播放'); play.type = 'button';
  play.onclick = () => { video.currentTime = Math.max(0, Number(f.time_s) - 3); video.play(); };
  head.append(play);
  c.append(head);
  const ans = el('div', 'answer');
  ans.append(el('strong', '', f.move_zh || '（没有答案）'), el('span', 'meta', f.move_en ? `  ${f.move_en}` : ''));
  c.append(ans, el('div', 'meta', `目录条目 ${f.entries || '—'}；这一次出招 ${f.chain || '—'}`));
  const ul = el('ul', 'hits');
  f.hits.split(' ｜ ').filter(Boolean).forEach((h) => ul.append(el('li', '', h)));
  c.append(ul);
  if (f.flags) c.append(el('div', 'warnline', '⚠ ' + f.flags));
  if (f.stale) c.append(el('div', 'warnline', '⚠ 你核对之后答案变了，请再看一次'));
  const img = el('img'); img.loading = 'lazy'; img.src = `/thumb/${encodeURIComponent(r.id)}/${encodeURIComponent(f.key)}.jpg`;
  img.onclick = () => img.classList.toggle('big');
  c.append(img);
  const acts = el('div', 'actions'), note = el('div', 'saved');
  const sel = el('select');
  const phaseMoves = MOVES.filter((m) => m.phases.includes(String(f.phase))), others = MOVES.filter((m) => !m.phases.includes(String(f.phase)));
  sel.append(new Option('选正确的招式…', ''));
  phaseMoves.forEach((m) => sel.append(new Option(m.zh, m.slug)));
  others.forEach((m) => sel.append(new Option(`${m.zh}（不在第 ${f.phase} 阶段）`, m.slug)));
  sel.append(new Option('不是这些招式里的（写在备注里）', 'other'));
  sel.value = f.correct_move || '';
  sel.hidden = f.verdict !== 'wrong';
  const ta = el('textarea'); ta.placeholder = '备注（可选）'; ta.value = f.review_note || '';
  const set = async (v) => {
    f.verdict = v; if (v !== 'wrong') { sel.value = ''; } f.correct_move = sel.value; note.textContent = '保存中…';
    try { await post({ rec: r.id, key: f.key, time_s: f.time_s, proposed: f.move, verdict: v, correct_move: sel.value, note: ta.value }, '/api/move'); note.textContent = '已保存'; f.stale = false; }
    catch (err) { note.textContent = '保存失败：' + err.message; }
    sel.hidden = v !== 'wrong';
    c.className = 'card ' + (v || ''); [...acts.querySelectorAll('button[data-v]')].forEach((b) => b.classList.toggle('on', b.dataset.v === v)); counts();
  };
  for (const [v, label] of Object.entries(VERDICT)) {
    const b = el('button', v + (f.verdict === v ? ' on' : ''), label); b.type = 'button'; b.dataset.v = v; b.onclick = () => set(v); acts.append(b);
  }
  const reset = el('button', '', '↺'); reset.type = 'button'; reset.title = '恢复成待核对'; reset.onclick = () => { ta.value = ''; set(''); };
  sel.onchange = () => set('wrong');
  acts.append(reset, sel, ta, note);
  let timer = null;
  ta.oninput = () => { clearTimeout(timer); timer = setTimeout(() => set(f.verdict), 1000); };
  c.append(acts);
  return c;
}
function summary() {
  const r = recs[cur], by = {};
  for (const f of r.failures) {
    const slug = f.verdict === 'wrong' && f.correct_move ? f.correct_move : f.move;
    const name = slug === 'other' ? '其他' : (MOVE[slug] ? MOVE[slug].zh : (f.move_zh || '（没有答案）'));
    const row = by[name] || (by[name] = { damage: 0, posture_break: 0, death: 0, all: 0 });
    row[f.type] += 1; row.all += 1;
  }
  const rows = Object.entries(by).sort((a, b) => b[1].all - a[1].all);
  const t = el('table'), head = el('tr');
  ['招式', '扣血', '被打崩', '死亡', '合计'].forEach((h, i) => head.append(el('th', i ? 'n' : '', h)));
  t.append(head);
  rows.forEach(([name, n]) => { const tr = el('tr'); tr.append(el('td', '', name), el('td', 'n', n.damage), el('td', 'n', n.posture_break), el('td', 'n', n.death), el('td', 'n', n.all)); t.append(tr); });
  document.getElementById('summary').replaceChildren(el('div', 'type', `按招式汇总（${r.failures.length} 次失败，核对过的按你的修改算）`), t);
}
function missed() {
  const r = recs[cur];
  document.getElementById('missed').replaceChildren(...r.missed.map((m) => {
    const li = el('li', '', `${TYPE[m.type]} ${fmt(m.time_s)}${m.note ? '：' + m.note : ''} `);
    const go = el('button', '', '▶'); go.type = 'button'; go.onclick = () => { video.currentTime = Math.max(0, Number(m.time_s) - 2); video.play(); };
    const del = el('button', '', '删除'); del.type = 'button';
    del.onclick = async () => { await post({ rec: r.id, key: m.key, type: m.type, time_s: m.time_s, verdict: '', note: '' }); r.missed = r.missed.filter((x) => x !== m); missed(); counts(); };
    li.append(go, del); return li;
  }));
}
document.getElementById('usenow').onclick = () => { document.getElementById('addtime').value = video.currentTime.toFixed(2); };
document.getElementById('addform').onsubmit = async (ev) => {
  ev.preventDefault();
  const r = recs[cur], type = document.getElementById('addtype').value, t = Number(document.getElementById('addtime').value), note = document.getElementById('addnote').value;
  if (!(t >= 0)) return;
  const key = await post({ rec: r.id, type, time_s: t, verdict: 'missed', note, key: `missed:${type}@${t.toFixed(2)}` });
  r.missed.push({ key, type, time_s: t.toFixed(3), note, verdict: 'missed' }); r.missed.sort((a, b) => a.time_s - b.time_s);
  document.getElementById('addnote').value = ''; missed(); counts();
};
function render(newRec) {
  if (mode === 'moves' && !recs[cur].failures.length) {
    const i = recs.findIndex((r) => r.failures.length);
    if (i >= 0 && i !== cur) { cur = i; newRec = true; }
  }
  tabs(); counts();
  const r = recs[cur];
  if (newRec) { video.src = `/video/${encodeURIComponent(r.id)}`; }
  document.getElementById('hint').textContent = HINT[mode];
  document.getElementById('addform').hidden = mode === 'moves';
  document.getElementById('missed').hidden = mode === 'moves';
  document.getElementById('summary').hidden = mode !== 'moves';
  const keep = { '全部': () => true, '待核对': (e) => !e.verdict, '扣血': (e) => e.type === 'damage', '被打崩': (e) => e.type === 'posture_break', '死亡': (e) => e.type === 'death' || e.type === 'resurrection', '忍杀': (e) => e.type === 'deathblow', '有提示': (e) => e.flags || e.stale }[filter];
  const items = mode === 'moves' ? r.failures : r.events;
  const shown = items.filter(keep);
  const make = mode === 'moves' ? (e) => fcard(r, e) : (e) => card(r, e);
  document.getElementById('list').replaceChildren(...(shown.length ? shown.map(make) : [el('p', 'hint', mode === 'moves' && !items.length ? '这个录像还没有招式答案（只有开发者菜单录像有）。' : '没有符合这个筛选的条目。')]));
  if (mode === 'events') missed();
}
render(true);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        try:
            if path in ("/", "/index.html"):
                payload = json.dumps(page_data(), ensure_ascii=False).replace("</", "<\\/")
                return self._send(200, PAGE.replace("__DATA__", payload), "text/html; charset=utf-8")
            m = re.fullmatch(r"/thumb/([^/]+)/([^/]+\.jpg)", path)
            if m:
                rec_id, name = unquote(m.group(1)), unquote(m.group(2))
                if rec_id not in recordings() or "/" in name or "\\" in name:
                    return self._send(404, "not found", "text/plain")
                f = work_dir(rec_id) / "thumbs" / name
                return self._send(200, f.read_bytes(), "image/jpeg") if f.exists() else self._send(404, "not found", "text/plain")
            m = re.fullmatch(r"/video/([^/]+)", path)
            if m:
                return self.video(unquote(m.group(1)))
            return self._send(404, "not found", "text/plain; charset=utf-8")
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass

    def video(self, rec_id):
        recs = recordings()
        if rec_id not in recs:
            return self._send(404, "not found", "text/plain")
        f = video_path(recs[rec_id])
        size = f.stat().st_size
        rng = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range", "") or "")
        start, end = 0, size - 1
        if rng:
            if rng.group(1):
                start = int(rng.group(1))
                end = int(rng.group(2)) if rng.group(2) else size - 1
            else:
                start = size - int(rng.group(2))
        end = min(end, start + 8 * 1024 * 1024 - 1, size - 1)       # serve at most 8 MB per request
        self.send_response(206 if rng else 200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if rng:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with open(f, "rb") as fh:
            fh.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = fh.read(min(1024 * 1024, left))
                if not chunk:
                    break
                self.wfile.write(chunk)
                left -= len(chunk)

    def do_POST(self):
        handlers = {"/api/review": save, "/api/move": save_move}
        if self.path not in handlers:
            return self._send(404, "not found", "text/plain")
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8"))
            key = handlers[self.path](body["rec"], body)
            self._send(200, json.dumps({"ok": True, "key": key}), "application/json")
        except Exception as ex:  # noqa: BLE001
            self._send(400, json.dumps({"ok": False, "error": str(ex)}, ensure_ascii=False), "application/json")

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8770
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"失败事件核对: http://127.0.0.1:{port}  (Ctrl+C 停止)")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
