import type { Boss, BossAnalytics, RecentAnalytics } from "../types";
import { topKeys } from "../utils/analytics";
import { getMoveName } from "../utils/moves";

interface AnalyticsPanelProps {
  boss: Boss;
  analytics: BossAnalytics;
}

function describeTop(keys: string[], label: (key: string) => string, empty: string): string {
  if (keys.length === 0) return empty;
  const names = keys.map(label).join(", ");
  return keys.length > 1 ? `${names} (tied)` : names;
}

function recentLabel(recent: RecentAnalytics): string {
  return recent.total_attempts < recent.window_size
    ? `Last ${recent.total_attempts} (all so far)`
    : `Last ${recent.window_size}`;
}

export default function AnalyticsPanel({ boss, analytics }: AnalyticsPanelProps) {
  if (analytics.total_attempts === 0) {
    return (
      <section className="analytics-panel">
        <h2>Your Analytics</h2>
        <p>Record an attempt to start seeing analytics.</p>
      </section>
    );
  }

  const { recent } = analytics;
  const recentHeader = recentLabel(recent);
  const phaseLabel = (phase: string) => `Phase ${phase}`;
  const moveLabel = (moveId: string) => getMoveName(boss, moveId) ?? moveId;

  const phaseRows = Object.keys(analytics.failure_by_phase).sort((a, b) => Number(a) - Number(b));
  const moveRows = Object.keys(analytics.failure_by_move).sort(
    (a, b) => analytics.failure_by_move[b] - analytics.failure_by_move[a]
  );

  return (
    <section className="analytics-panel">
      <h2>Your Analytics</h2>

      <div className="analytics-summary">
        <div>
          <h3>Main Bottleneck</h3>
          <dl className="comparison">
            <dt>All attempts</dt>
            <dd>{describeTop(topKeys(analytics.failure_by_phase), phaseLabel, "N/A")}</dd>
            <dt>{recentHeader}</dt>
            <dd>{describeTop(topKeys(recent.failure_by_phase), phaseLabel, "N/A")}</dd>
          </dl>
        </div>
        <div>
          <h3>Most Common Failure</h3>
          <dl className="comparison">
            <dt>All attempts</dt>
            <dd>{describeTop(topKeys(analytics.failure_by_move), moveLabel, "Not enough data")}</dd>
            <dt>{recentHeader}</dt>
            <dd>{describeTop(topKeys(recent.failure_by_move), moveLabel, "Not enough data")}</dd>
          </dl>
        </div>
      </div>

      {phaseRows.length > 0 && (
        <table className="failure-breakdown">
          <caption>Failure Breakdown by Phase</caption>
          <thead>
            <tr>
              <th scope="col">Phase</th>
              <th scope="col">All attempts</th>
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
          <caption>Failure Breakdown by Move</caption>
          <thead>
            <tr>
              <th scope="col">Move</th>
              <th scope="col">All attempts</th>
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
