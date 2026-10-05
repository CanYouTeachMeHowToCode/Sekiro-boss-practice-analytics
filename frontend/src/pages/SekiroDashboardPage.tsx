import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getSekiroAnalytics } from "../api/sekiro";
import { bossName } from "../i18n/content";
import { formatPhase, localeFor, useLanguage } from "../i18n/language";
import type { Language, Translate } from "../i18n/language";
import type { BossComparisonRow, RecentAttempt, SekiroAnalytics } from "../types";

type LoadState = "loading" | "error" | "ready";

function joinNames(ids: string[], names: Record<string, string>, t: Translate): string {
  const joined = ids.map((id) => names[id] ?? id).join(t("listSeparator"));
  return ids.length > 1 ? t("tied", { names: joined }) : joined;
}

function bestResult(row: BossComparisonRow, t: Translate): string {
  if (row.defeated) return t("result.victory");
  return row.best_phase !== null ? t("sekiro.bestPhase", { n: row.best_phase, total: row.total_phases }) : "—";
}

function attemptCause(attempt: RecentAttempt, language: Language, t: Translate): string | null {
  if (attempt.result === "victory") return null;
  if (attempt.failure_move_name) {
    return language === "zh" && attempt.failure_move_name_zh ? attempt.failure_move_name_zh : attempt.failure_move_name;
  }
  if (attempt.failure_category === "other") return t("cause.other");
  return t("cause.notSure");
}

function formatTime(timestamp: string, language: Language): string {
  return new Date(timestamp).toLocaleString(localeFor(language), {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function SekiroDashboardPage() {
  const { language, t } = useLanguage();
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
        <p>{t("loading")}</p>
      </main>
    );
  }

  if (state === "error" || !data) {
    return (
      <main className="page">
        <p role="alert">{t("sekiro.loadError")}</p>
      </main>
    );
  }

  const names = Object.fromEntries(data.bosses.map((b) => [b.id, bossName(b, language)]));
  const mostPracticedCount = Math.max(0, ...data.bosses.map((b) => b.attempts));

  return (
    <main className="page">
      <h1>{t("sekiro.heading")}</h1>
      <p>
        <Link to="/bosses">{t("sekiro.browseAll")}</Link>
      </p>

      <div className="stat-grid">
        <div>
          <h3>{t("sekiro.bossesAttempted")}</h3>
          <p>
            {data.bosses_attempted} / {data.total_bosses}
          </p>
        </div>
        <div>
          <h3>{t("sekiro.bossesDefeated")}</h3>
          <p>{data.bosses_defeated}</p>
        </div>
        <div>
          <h3>{t("sekiro.totalAttempts")}</h3>
          <p>{data.total_attempts}</p>
        </div>
        <div>
          <h3>{t("sekiro.lastDays", { n: data.recent_window_days })}</h3>
          <p>{data.attempts_in_recent_window}</p>
        </div>
      </div>

      <div className="analytics-summary">
        <div>
          <h3>{t("sekiro.mostPracticed")}</h3>
          <p>
            {data.most_practiced_bosses.length > 0
              ? t("sekiro.namesWithAttempts", {
                  names: joinNames(data.most_practiced_bosses, names, t),
                  count: mostPracticedCount,
                })
              : t("sekiro.noAttemptsYet")}
          </p>
        </div>
        <div>
          <h3>{t("sekiro.mostAttemptsToDefeat")}</h3>
          <p>
            {data.bosses_requiring_most_attempts.length > 0
              ? t("sekiro.namesWithAttempts", {
                  names: joinNames(data.bosses_requiring_most_attempts, names, t),
                  count: data.most_attempts_to_defeat ?? 0,
                })
              : t("sekiro.noneDefeated")}
          </p>
        </div>
      </div>

      <section className="boss-comparison">
        <h2>{t("sekiro.comparison")}</h2>
        <div className="table-scroll">
          <table className="failure-breakdown">
            <thead>
              <tr>
                <th scope="col">{t("sekiro.col.boss")}</th>
                <th scope="col">{t("sekiro.col.attempts")}</th>
                <th scope="col">{t("sekiro.col.bestResult")}</th>
                <th scope="col">{t("sekiro.col.defeated")}</th>
                <th scope="col">{t("sekiro.col.firstVictory")}</th>
              </tr>
            </thead>
            <tbody>
              {data.bosses.map((boss) => (
                <tr key={boss.id}>
                  <td>
                    <Link to={`/bosses/${boss.id}`}>{bossName(boss, language)}</Link>
                  </td>
                  <td>{boss.attempts}</td>
                  <td>{bestResult(boss, t)}</td>
                  <td>{boss.defeated ? t("yes") : t("no")}</td>
                  <td>
                    {boss.attempts_until_first_victory !== null
                      ? t("boss.attemptNumber", { n: boss.attempts_until_first_victory })
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="attempt-history">
        <h2>{t("sekiro.recentPractice")}</h2>
        {data.recent_attempts.length === 0 ? (
          <p>{t("sekiro.noRecent")}</p>
        ) : (
          <ul>
            {data.recent_attempts.map((attempt) => {
              const cause = attemptCause(attempt, language, t);
              return (
                <li key={attempt.attempt_id} className={`attempt ${attempt.result}`}>
                  <Link to={`/bosses/${attempt.boss_id}`}>
                    {bossName({ name: attempt.boss_name, name_zh: attempt.boss_name_zh }, language)}
                  </Link>
                  <span className="attempt-result">
                    {attempt.result === "victory"
                      ? t("result.victory")
                      : t("result.failedAt", { phase: formatPhase(attempt.phase_reached, language) })}
                  </span>
                  {cause && <span className="attempt-cause">{cause}</span>}
                  <span className="attempt-number">{formatTime(attempt.timestamp, language)}</span>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </main>
  );
}
