import type { Boss, BossAnalytics } from "../types";
import { getMoveName } from "../utils/moves";

interface AnalyticsPanelProps {
  boss: Boss;
  analytics: BossAnalytics;
}

export default function AnalyticsPanel({ boss, analytics }: AnalyticsPanelProps) {
  const failureByMoveRows = Object.entries(analytics.failure_by_move).sort((a, b) => b[1] - a[1]);
  const failureByPhaseRows = Object.entries(analytics.failure_by_phase).sort(
    (a, b) => Number(a[0]) - Number(b[0])
  );

  return (
    <section className="analytics-panel">
      <h2>Your Analytics</h2>

      {analytics.total_attempts === 0 ? (
        <p>Record an attempt to start seeing analytics.</p>
      ) : (
        <>
          <div className="analytics-summary">
            <div>
              <h3>Main Bottleneck</h3>
              <p>{analytics.main_bottleneck_phase !== null ? `Phase ${analytics.main_bottleneck_phase}` : "N/A"}</p>
            </div>
            <div>
              <h3>Most Common Failure</h3>
              <p>
                {analytics.most_common_failure_move
                  ? getMoveName(boss, analytics.most_common_failure_move) ?? analytics.most_common_failure_move
                  : "Not enough data"}
              </p>
            </div>
          </div>

          {failureByPhaseRows.length > 0 && (
            <table className="failure-breakdown">
              <caption>Failure Breakdown by Phase</caption>
              <tbody>
                {failureByPhaseRows.map(([phase, count]) => (
                  <tr key={phase}>
                    <td>{`Phase ${phase}`}</td>
                    <td>{count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {failureByMoveRows.length > 0 && (
            <table className="failure-breakdown">
              <caption>Failure Breakdown by Move</caption>
              <tbody>
                {failureByMoveRows.map(([moveId, count]) => (
                  <tr key={moveId}>
                    <td>{getMoveName(boss, moveId) ?? moveId}</td>
                    <td>{count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </section>
  );
}
