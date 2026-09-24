import { formatPhase, useLanguage } from "../i18n/language";
import type { Translate } from "../i18n/language";
import type { Boss, BossAnalytics, RecentAnalytics } from "../types";
import { topKeys } from "../utils/analytics";
import { getMoveName } from "../utils/moves";

interface AnalyticsPanelProps {
  boss: Boss;
  analytics: BossAnalytics;
}

function describeTop(keys: string[], label: (key: string) => string, empty: string, t: Translate): string {
  if (keys.length === 0) return empty;
  const names = keys.map(label).join(t("listSeparator"));
  return keys.length > 1 ? t("tied", { names }) : names;
}

function recentLabel(recent: RecentAnalytics, t: Translate): string {
  return recent.total_attempts < recent.window_size
    ? t("analytics.lastAllSoFar", { n: recent.total_attempts })
    : t("analytics.lastN", { n: recent.window_size });
}

export default function AnalyticsPanel({ boss, analytics }: AnalyticsPanelProps) {
  const { language, t } = useLanguage();

  if (analytics.total_attempts === 0) {
    return (
      <section className="analytics-panel">
        <h2>{t("analytics.heading")}</h2>
        <p>{t("analytics.empty")}</p>
      </section>
    );
  }

  const { recent } = analytics;
  const recentHeader = recentLabel(recent, t);
  const phaseLabel = (phase: string) => formatPhase(phase, language);
  const moveLabel = (moveId: string) => getMoveName(boss, moveId, language) ?? moveId;

  const phaseRows = Object.keys(analytics.failure_by_phase).sort((a, b) => Number(a) - Number(b));
  const moveRows = Object.keys(analytics.failure_by_move).sort(
    (a, b) => analytics.failure_by_move[b] - analytics.failure_by_move[a]
  );
  const notApplicable = t("analytics.notApplicable");
  const notEnoughData = t("analytics.notEnoughData");

  return (
    <section className="analytics-panel">
      <h2>{t("analytics.heading")}</h2>

      <div className="analytics-summary">
        <div>
          <h3>{t("analytics.mainBottleneck")}</h3>
          <dl className="comparison">
            <dt>{t("analytics.allAttempts")}</dt>
            <dd>{describeTop(topKeys(analytics.failure_by_phase), phaseLabel, notApplicable, t)}</dd>
            <dt>{recentHeader}</dt>
            <dd>{describeTop(topKeys(recent.failure_by_phase), phaseLabel, notApplicable, t)}</dd>
          </dl>
        </div>
        <div>
          <h3>{t("analytics.mostCommonFailure")}</h3>
          <dl className="comparison">
            <dt>{t("analytics.allAttempts")}</dt>
            <dd>{describeTop(topKeys(analytics.failure_by_move), moveLabel, notEnoughData, t)}</dd>
            <dt>{recentHeader}</dt>
            <dd>{describeTop(topKeys(recent.failure_by_move), moveLabel, notEnoughData, t)}</dd>
          </dl>
        </div>
      </div>

      {phaseRows.length > 0 && (
        <table className="failure-breakdown">
          <caption>{t("analytics.byPhase")}</caption>
          <thead>
            <tr>
              <th scope="col">{t("analytics.phase")}</th>
              <th scope="col">{t("analytics.allAttempts")}</th>
              <th scope="col">{recentHeader}</th>
            </tr>
          </thead>
          <tbody>
            {phaseRows.map((phase) => (
              <tr key={phase}>
                <td>{phaseLabel(phase)}</td>
                <td>{analytics.failure_by_phase[phase]}</td>
                <td>{recent.failure_by_phase[phase] ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {moveRows.length > 0 && (
        <table className="failure-breakdown">
          <caption>{t("analytics.byMove")}</caption>
          <thead>
            <tr>
              <th scope="col">{t("analytics.move")}</th>
              <th scope="col">{t("analytics.allAttempts")}</th>
              <th scope="col">{recentHeader}</th>
            </tr>
          </thead>
          <tbody>
            {moveRows.map((moveId) => (
              <tr key={moveId}>
                <td>{moveLabel(moveId)}</td>
                <td>{analytics.failure_by_move[moveId]}</td>
                <td>{recent.failure_by_move[moveId] ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
