"""Reliability validation (V4 M2): the owner's answers against what the frozen pipeline reported.

Usage: python -I reliability.py snapshot <recording id | all>
       python -I reliability.py report [--set development|test|all]

The answers of a recording, in research/ground_truth/annotations/<ruleset>/genichiro/<recording>/:
- hud_events.csv, the owner's review of the detected events (review_events.py, 事件 view). The real failure events are
  the detected ones marked correct and the ones the owner added as missed.
- failure_truth.csv, the failures and their moves: key, time_s, events, move, two_slashes, merge_prev, source, note,
  updated. A row is one failure: its events (detected keys such as damage@28.2, or missed:damage@12.34 for an event the
  owner added) and its move (a product move slug, `other`, or `unsure` when the owner cannot tell). two_slashes marks
  Floating Passage's opening two slashes without their follow-up, where Two-Hit Slash is right too (the owner's rule,
  2026-10-16); merge_prev joins the row to the one before it. For a test recording the review page's blind 招式 view
  writes it, without showing the system's answer. For the M1 recordings `snapshot` writes it once from the M1 reviews
  (failure_moves.csv, with the overlay answers or the predictions the owner reviewed).

`report` compares them with work/<id>/events.csv and failure_predictions.csv, for the recordings of a set
(recordings.json "set": development is everything M1 was built and tuned on, test the M2 recordings held out until the
pipeline was frozen), and writes work/reliability_report.md and work/reliability_failures.csv:
- events, per type: precision (detected events that are real) and recall (real events that were detected);
- failures: a real failure and a reported one are the same when they share a real event. A real failure with no
  reported one is missed, a reported one with no real event is false, one real failure reported as two is counted
  twice, two real failures reported as one are merged;
- moves, on the failures reported once: how often the system was sure, how often it was right when sure, and the
  top-1 and top-3 accuracy over all of them (the owner's rules on moves that look the same, common.accepted());
- failures per move: the owner's counts against the counts the report would show.
Each rate comes with a 95% Wilson interval, because a few dozen failures leave a wide margin.
"""
import csv
import io
import math
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FA, REPO, TWO_SLASHES, WORK, accepted, annotation_dir, observation_dir, recordings, work_dir  # noqa: E402
from review_events import drop_repeats, match, product_moves  # noqa: E402

ZH = {m["slug"]: m["zh"] for m in product_moves()}

FAILURE_TYPES = ("damage", "posture_break", "death")
TYPE_ZH = {"damage": "扣血", "posture_break": "被打崩", "death": "死亡"}
TRUTH_FIELDS = ["key", "time_s", "events", "move", "two_slashes", "merge_prev", "source", "note", "updated"]
# the owner's word on a failure of the M1 test recordings that the M1 review file does not hold: castle-1 238.4 s is
# Floating Passage's opening two slashes without the follow-up, so Two-Hit Slash, which was proposed, is right (2026-10-16)
M1_TWO_SLASHES = {("2026-10-16-castle-1", "death@238.4")}


def read(path):
    return list(csv.DictReader(open(path, encoding="utf-8"))) if path.exists() else []


def write(path, fields, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\r\n")
    w.writeheader()
    w.writerows(rows)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(buf.getvalue(), encoding="utf-8", newline="")
    os.replace(tmp, path)


def key_time(key):
    return float(key.split("@")[1])


def truth_moves(row, chain=""):
    """The moves that count as right for a truth row (an empty set for `other` and `unsure`)."""
    if row["move"] in ("other", "unsure", ""):
        return set()
    if row.get("two_slashes"):
        return set(TWO_SLASHES)
    return set(accepted(row["move"], chain))


# ---------------------------------------------------------------- snapshot of the M1 reviews


def snapshot(rec_id, rec):
    out = annotation_dir(rec) / "failure_truth.csv"
    if out.exists():
        print(f"{rec_id}: {out.name} exists, left as it is")
        return
    overlay = observation_dir(rec) is not None
    failures = read(work_dir(rec_id) / ("failure_answers.csv" if overlay else "failure_predictions.csv"))
    reviews = {r["key"]: r for r in read(annotation_dir(rec) / "failure_moves.csv")}
    used, rows = set(), []
    for f in failures:
        r = reviews.get(f["key"]) or next((reviews[k] for k in f["events"].split() if k in reviews), None)
        if r is None or r["verdict"] not in ("correct", "wrong"):
            move, note = "unsure", "M1 没有核对过" if r is None else f"M1 核对为不确定：{r['note']}"
        else:
            move = r["proposed"] if r["verdict"] == "correct" else r["correct_move"]
            note = r["note"]
            if r["key"] in used:
                print(f"  ! {rec_id}: review {r['key']} matches two failures")
            used.add(r["key"])
        two = (overlay and move in TWO_SLASHES and accepted(move, f["chain"]) == TWO_SLASHES) or \
            (rec_id, f["key"]) in M1_TWO_SLASHES
        rows.append({"key": f["key"], "time_s": f["time_s"], "events": f["events"], "move": move,
                     "two_slashes": "1" if two else "", "merge_prev": "1" if r and r.get("merge_prev") else "",
                     "source": "M1 review of the overlay answers" if overlay else "M1 review of the predictions",
                     "note": note, "updated": datetime.now().isoformat(timespec="seconds")})
    for k in set(reviews) - used:
        if reviews[k]["verdict"] in ("correct", "wrong"):
            print(f"  ! {rec_id}: review {k} matches no failure")
    write(out, TRUTH_FIELDS, rows)
    print(f"{rec_id}: {len(rows)} failures -> {out}")


# ---------------------------------------------------------------- report


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p, d = k / n, 1 + z * z / n
    c, h = (p + z * z / (2 * n)) / d, z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def rate(k, n):
    if n == 0:
        return "—"
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {k / n:.0%}（{lo:.0%}–{hi:.0%}）"


class Recording:
    """One recording's answers and reports, matched."""

    def __init__(self, rec_id, rec):
        self.id, self.problems = rec_id, []
        work, ann = work_dir(rec_id), annotation_dir(rec)
        detected = drop_repeats(read(work / "events.csv"))      # an event reported several times counts once
        self.repeats = [(e["key"], e["repeats"]) for e in detected if e["repeats"] > 1]
        self.detected = [e for e in detected if e["type"] in FAILURE_TYPES]
        reviews = [r for r in read(ann / "hud_events.csv") if r["type"] in FAILURE_TYPES]
        # each detected event: real, false (marked wrong), unsure or not reviewed
        self.status, used = {}, set()
        for e in self.detected:
            r = next((r for i, r in enumerate(reviews) if i not in used and r["verdict"] != "missed" and match(r, e)), None)
            if r is None:
                r = next((r for i, r in enumerate(reviews) if i not in used and r["verdict"] == "missed" and match(r, e)), None)
            if r is not None:
                used.add(reviews.index(r))
            self.status[e["key"]] = {"correct": "real", "missed": "real", "wrong": "false", "unsure": "unsure"}.get(
                r["verdict"] if r else "", "unreviewed")
        self.missed = [r for i, r in enumerate(reviews) if r["verdict"] == "missed" and i not in used]
        # the real failures: the truth rows, merged where the owner said so, keeping only real events
        truth = sorted(read(ann / "failure_truth.csv"), key=lambda r: float(r["time_s"]))
        real_missed = {r["key"] for r in self.missed}
        self.truth = []
        for row in truth:
            keys = row["events"].split()
            real = {k for k in keys if self.status.get(k) == "real"} | {k for k in keys if k in real_missed}
            if row.get("merge_prev") and self.truth:
                self.truth[-1]["events"] |= real
                continue
            if real:
                self.truth.append({"row": row, "events": real, "moves": truth_moves(row), "t": float(row["time_s"])})
        covered = set().union(*(t["events"] for t in self.truth)) if self.truth else set()
        real_all = {k for k, s in self.status.items() if s == "real"} | real_missed
        if real_all - covered:
            self.problems.append(f"{len(real_all - covered)} 个真实事件没有标招式：{' '.join(sorted(real_all - covered, key=key_time))}")
        if any(s == "unreviewed" for s in self.status.values()):
            self.problems.append(f"{sum(s == 'unreviewed' for s in self.status.values())} 个检测到的事件还没核对")
        self.reported = []
        for p in read(work / "failure_predictions.csv"):
            cands = [c.rsplit(":", 1) for c in p["candidates"].split()]
            self.reported.append({"row": p, "events": set(p["events"].split()), "t": float(p["time_s"]),
                                  "top": [c[0] for c in cands], "sure": p.get("certain", "1") == "1",
                                  "confidence": p.get("confidence", "")})
        self.components()

    def components(self):
        """Group real and reported failures that share a real event."""
        n_t = len(self.truth)
        parent = list(range(n_t + len(self.reported)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        for j, p in enumerate(self.reported):
            for i, t in enumerate(self.truth):
                if t["events"] & p["events"]:
                    parent[find(i)] = find(n_t + j)
        groups = {}
        for i in range(len(parent)):
            groups.setdefault(find(i), []).append(i)
        self.groups = []
        for members in groups.values():
            ts = [self.truth[i] for i in members if i < n_t]
            ps = [self.reported[i - n_t] for i in members if i >= n_t]
            if ps and not ts and not any(self.status.get(k) == "real" for p in ps for k in p["events"]):
                kind = "false"
            elif not ts:
                kind = "unlabelled"          # real events the owner has not given a move yet (listed as a problem)
            elif not ps:
                kind = "missed"
            elif len(ts) == 1 and len(ps) == 1:
                kind = "matched"
            elif len(ts) == 1:
                kind = "split"
            elif len(ps) == 1:
                kind = "merged"
            else:
                kind = "tangled"
            self.groups.append({"kind": kind, "truth": ts, "reported": ps,
                                "t": min([x["t"] for x in ts + ps])})
        self.groups.sort(key=lambda g: g["t"])


def name(slug):
    return {"other": "其他", "unsure": "看不出来", "": "—"}.get(slug, ZH.get(slug, slug))


# the scripts that turn a recording into reported failures: the version the M2 plan freezes. The review page, the
# registry and this report are left out, since changing them changes no result
PIPELINE = ["common.py", "hud_pipeline.py", "hud_read.py", "death_screen.py", "events.py", "lockon.py", "boss_track.py",
            "boss_features.py", "overlay_mask.py", "failure_answers.py", "move_match.py"]


def commit_state():
    """The last commit that changed the pipeline's scripts, and whether any of them has uncommitted changes."""
    paths = [str(FA / "scripts" / f) for f in PIPELINE]
    head = subprocess.run(["git", "-C", str(REPO), "log", "-1", "--format=%h", "--", *paths],
                          capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--", *paths],
                           capture_output=True, text=True).stdout.strip()
    return head + ("（流水线脚本有未提交的改动）" if dirty else "")


def report(which):
    recs = [Recording(i, r) for i, r in recordings().items()
            if which == "all" or r.get("set", "development") == which]
    recs = [r for r in recs if r.detected or r.truth]
    md = [f"# 可靠性验证报告（{which}）", "", f"代码版本 {commit_state()}，生成于 {datetime.now():%Y-%m-%d %H:%M}。", ""]
    problems = [f"- {r.id}：{p}" for r in recs for p in r.problems]
    if problems:
        md += ["**答案还不完整，下面的数字不算数：**", "", *problems, ""]
    repeats = [f"{r.id} {k} ×{n}" for r in recs for k, n in r.repeats]
    if repeats:
        md += ["同一时刻被重复报告的事件，按 1 次算，不算误检（你定，2026-10-25）：" + "，".join(repeats) + "。", ""]

    # events
    md += ["## 失败事件", "", "| 类型 | 真实 | 检测到 | 精确率（检测到的是真的） | 召回率（真的被检测到） | 你不确定 |", "|---|---|---|---|---|---|"]
    for kind in (*FAILURE_TYPES, None):
        real = det = hit = unsure = 0
        for r in recs:
            for e in r.detected:
                if kind and e["type"] != kind:
                    continue
                s = r.status[e["key"]]
                det += s in ("real", "false")
                hit += s == "real"
                unsure += s == "unsure"
            real += sum(1 for e in r.detected if (not kind or e["type"] == kind) and r.status[e["key"]] == "real")
            real += sum(1 for m in r.missed if not kind or m["type"] == kind)
        md.append(f"| {TYPE_ZH[kind] if kind else '合计'} | {real} | {det} | {rate(hit, det)} | {rate(hit, real)} | {unsure} |")

    # failures
    count = {k: sum(1 for r in recs for g in r.groups if g["kind"] == k) for k in ("matched", "missed", "false", "split", "merged", "tangled")}
    n_truth = sum(len(r.truth) for r in recs)
    n_rep = sum(len(r.reported) for r in recs)
    ok = count["matched"] + count["split"] + count["merged"]
    md += ["", "## 失败（合并之后）", "", f"- 真实失败 {n_truth} 次，报告 {n_rep} 次",
           f"- 精确率（报告的失败是真的）{rate(ok, n_rep)}；召回率（真的失败被报告）{rate(ok, n_truth)}",
           f"- 漏掉 {count['missed']} 次，报了不存在的 {count['false']} 次",
           f"- 一次失败被拆成两次以上 {count['split']} 次，几次失败被合成一次 {count['merged']} 次，交错 {count['tangled']} 次"]

    # moves
    rows, judged = [], []
    for r in recs:
        for g in r.groups:
            for t in g["truth"] or [None]:
                for p in g["reported"] or [None]:
                    rows.append((r, g, t, p))
            if g["kind"] == "matched" and g["truth"][0]["row"]["move"] != "unsure":
                judged.append((r, g["truth"][0], g["reported"][0]))
    n = len(judged)
    sure = [(t, p) for _, t, p in judged if p["sure"]]
    right = lambda t, p, k=1: bool(set(p["top"][:k]) & t["moves"])  # noqa: E731
    md += ["", "## 招式（只算一次失败对应一次报告的）", "",
           f"- 你标了招式的 {n} 次（另有 {sum(1 for r in recs for g in r.groups if g['kind'] == 'matched' and g['truth'][0]['row']['move'] == 'unsure')} 次你看不出来，不算）",
           f"- 系统有把握的 {rate(len(sure), n)}；有把握时答对 {rate(sum(right(t, p) for t, p in sure), len(sure))}",
           f"- 没把握的报告写\"可能是 A 或 B\"：正确答案在这两个里 "
           f"{rate(sum(right(t, p, 2) for _, t, p in judged if not p['sure']), n - len(sure))}",
           f"- 不管有没有把握：第一候选对 {rate(sum(right(t, p) for _, t, p in judged), n)}，前三里有 {rate(sum(right(t, p, 3) for _, t, p in judged), n)}"]

    # per move
    real_count, shown, unsure_count = {}, {}, {}
    for r in recs:
        for t in r.truth:
            real_count[t["row"]["move"]] = real_count.get(t["row"]["move"], 0) + 1
        for p in r.reported:
            d = shown if p["sure"] else unsure_count
            m = p["top"][0] if p["top"] else ""
            d[m] = d.get(m, 0) + 1
    moves = sorted(set(real_count) | set(shown) | set(unsure_count), key=lambda m: -real_count.get(m, 0))
    md += ["", "## 按招式的失败次数", "", "报告里写的是有把握的次数；不确定的单独列出，报告里会说\"招式不确定\"。", "",
           "| 招式 | 你标的 | 报告（有把握） | 差 | 报告（不确定，按第一候选） |", "|---|---|---|---|---|"]
    for m in moves:
        a, b = real_count.get(m, 0), shown.get(m, 0)
        md.append(f"| {name(m)} | {a} | {b} | {b - a:+d} | {unsure_count.get(m, 0)} |")

    # per recording
    md += ["", "## 每段录像", "", "| 录像 | 真实失败 | 报告 | 漏掉 | 不存在 | 拆开 | 合并 | 招式（有把握时对 / 有把握） | 第一候选 | 前三 |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for r in recs:
        js = [(t, p) for rr, t, p in judged if rr is r]
        c = {k: sum(1 for g in r.groups if g["kind"] == k) for k in ("missed", "false", "split", "merged")}
        sr = [(t, p) for t, p in js if p["sure"]]
        md.append(f"| {r.id} | {len(r.truth)} | {len(r.reported)} | {c['missed']} | {c['false']} | {c['split']} | {c['merged']} | "
                  f"{sum(right(t, p) for t, p in sr)}/{len(sr)} | {sum(right(t, p) for t, p in js)}/{len(js)} | "
                  f"{sum(right(t, p, 3) for t, p in js)}/{len(js)} |")

    # errors
    md += ["", "## 错误清单", ""]
    for r, g, t, p in rows:
        if g["kind"] == "matched" and t["row"]["move"] != "unsure" and right(t, p) and p["sure"]:
            continue
        what = {"missed": "漏掉", "false": "不存在的失败", "split": "被拆开", "merged": "被合并", "tangled": "交错",
                "unlabelled": "还没标招式",
                "matched": "招式不确定" if p and not p["sure"] else "认错招式"}[g["kind"]]
        if g["kind"] == "matched" and t["row"]["move"] == "unsure":
            continue
        if g["kind"] == "matched" and not p["sure"] and right(t, p):
            what = "不确定（第一候选其实对）"
        tt = f"{t['t']:.1f}s 你标 {name(t['row']['move'])}" if t else ""
        pp = f"{p['t']:.1f}s 报告 {' / '.join(name(m) for m in p['top'][:3])}{'' if p['sure'] else '（不确定）'}" if p else ""
        md.append(f"- {r.id} {what}：{'；'.join(x for x in (tt, pp) if x)}")

    out = WORK / "reliability_report.md"
    out.write_text("\n".join(md) + "\n", encoding="utf-8")
    flat = [{"recording": r.id, "kind": g["kind"], "truth_time": f"{t['t']:.3f}" if t else "",
             "truth_move": t["row"]["move"] if t else "", "truth_events": " ".join(sorted(t["events"], key=key_time)) if t else "",
             "reported_time": f"{p['t']:.3f}" if p else "", "reported_top3": " ".join(p["top"][:3]) if p else "",
             "sure": ("1" if p["sure"] else "0") if p else "", "confidence": p["confidence"] if p else "",
             "top1_right": ("1" if right(t, p) else "0") if t and p else "",
             "top3_right": ("1" if right(t, p, 3) else "0") if t and p else ""} for r, g, t, p in rows]
    if flat:
        write(WORK / "reliability_failures.csv", list(flat[0]), flat)
    print("\n".join(md))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1] == "snapshot":
        for rid, rec in recordings().items():
            if sys.argv[2] in ("all", rid):
                snapshot(rid, rec)
    elif sys.argv[1] == "report":
        report(sys.argv[sys.argv.index("--set") + 1] if "--set" in sys.argv else "development")
