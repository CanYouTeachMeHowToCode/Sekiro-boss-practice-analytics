import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getSekiroAnalytics } from "../api/sekiro";
import { formatMoveName } from "../utils/moves";
import type { BossComparisonRow, RecentAttempt, SekiroAnalytics } from "../types";

type LoadState = "loading" | "error" | "ready";

function joinNames(ids: string[], names: Record<string, string>): string {
  const joined = ids.map((id) => names[id] ?? id).join(", ");
  return ids.length > 1 ? `${joined} (tied)` : joined;
}

function bestResult(row: BossComparisonRow): string {
  if (row.defeated) return "Victory";
  return row.best_phase !== null ? `Phase ${row.best_phase} / ${row.total_phases}` : "—";
}

function attemptCause(attempt: RecentAttempt): string | null {
  if (attempt.result === "victory") return null;
  if (attempt.failure_move_name) return formatMoveName(attempt.failure_move_name, attempt.failure_move_name_zh);
  if (attempt.failure_category === "other") return "Other";
  return "Not Sure";
}

function formatTime(timestamp: string): string {
  return new Date(timestamp).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function SekiroDashboardPage() {
  const [data, setData] = useState<SekiroAnalytics | null>(null);
  const [state, setState] = useState<LoadState>("loading");

  useEffect(() => {
    let cancelled = false;
    getSekiroAnalytics()
      .then((result) => {
        if (cancelled) return;
        setData(result);
        setState("ready");
      })
      .catch(() => {
        if (!cancelled) setState("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (state === "loading") {
    return (
      <main className="page">
        <p>Loading…</p>
      </main>
    );
  }

  if (state === "error" || !data) {
    return (
      <main className="page">
        <p role="alert">Failed to load the Sekiro dashboard.</p>
      </main>
    );
  }

  const names = Object.fromEntries(data.bosses.map((b) => [b.id, b.name]));
  const mostPracticedCount = Math.max(0, ...data.bosses.map((b) => b.attempts));

  return (
    <main className="page">
      <h1>Sekiro Practice Dashboard</h1>
      <p>
        <Link to="/bosses">Browse all bosses →</Link>
      </p>

      <div className="stat-grid">
        <div>
          <h3>Bosses Attempted</h3>
          <p>
            {data.bosses_attempted} / {data.total_bosses}
          </p>
        </div>
        <div>
          <h3>Bosses Defeated</h3>
          <p>{data.bosses_defeated}</p>
        </div>
        <div>
          <h3>Total Attempts</h3>
          <p>{data.total_attempts}</p>
        </div>
        <div>
          <h3>Last {data.recent_window_days} Days</h3>
          <p>{data.attempts_in_recent_window}</p>
        </div>
      </div>

      <div className="analytics-summary">
        <div>
          <h3>Most Practiced Boss</h3>
          <p>
            {data.most_practiced_bosses.length > 0
              ? `${joinNames(data.most_practiced_bosses, names)} — ${mostPracticedCount} attempts`
              : "No attempts yet"}
          </p>
        </div>
        <div>
          <h3>Boss Requiring Most Attempts to Defeat</h3>
          <p>
            {data.bosses_requiring_most_attempts.length > 0
              ? `${joinNames(data.bosses_requiring_most_attempts, names)} — ${data.most_attempts_to_defeat} attempts`
              : "No boss defeated yet"}
          </p>
        </div>
      </div>

      <section className="boss-comparison">
        <h2>Boss Comparison</h2>
        <div className="table-scroll">
          <table className="failure-breakdown">
            <thead>
              <tr>
                <th scope="col">Boss</th>
                <th scope="col">Attempts</th>
                <th scope="col">Best Result</th>
                <th scope="col">Defeated</th>
                <th scope="col">First Victory</th>
              </tr>
            </thead>
            <tbody>
              {data.bosses.map((boss) => (
                <tr key={boss.id}>
                  <td>
                    <Link to={`/bosses/${boss.id}`}>{boss.name}</Link>
                    {boss.name_zh && <div className="boss-name-zh">{boss.name_zh}</div>}
                  </td>
                  <td>{boss.attempts}</td>
                  <td>{bestResult(boss)}</td>
                  <td>{boss.defeated ? "Yes" : "No"}</td>
                  <td>
                    {boss.attempts_until_first_victory !== null ? `Attempt #${boss.attempts_until_first_victory}` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="attempt-history">
        <h2>Recent Practice</h2>
        {data.recent_attempts.length === 0 ? (
          <p>No attempts recorded yet. Pick a boss to record your first attempt.</p>
        ) : (
          <ul>
            {data.recent_attempts.map((attempt) => {
              const cause = attemptCause(attempt);
              return (
                <li key={attempt.attempt_id} className={`attempt ${attempt.result}`}>
                  <Link to={`/bosses/${attempt.boss_id}`}>{attempt.boss_name}</Link>
                  <span className="attempt-result">
                    {attempt.result === "victory" ? "Victory" : `Failed — Phase ${attempt.phase_reached}`}
                  </span>
                  {cause && <span className="attempt-cause">{cause}</span>}
                  <span className="attempt-number">{formatTime(attempt.timestamp)}</span>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </main>
  );
}
