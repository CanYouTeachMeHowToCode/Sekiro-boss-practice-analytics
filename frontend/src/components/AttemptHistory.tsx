import type { Attempt, Boss } from "../types";
import { getFailureLabel } from "../utils/moves";

interface AttemptHistoryProps {
  boss: Boss;
  attempts: Attempt[];
}

export default function AttemptHistory({ boss, attempts }: AttemptHistoryProps) {
  return (
    <section className="attempt-history">
      <h2>Recent Attempts</h2>

      {attempts.length === 0 ? (
        <p>No attempts recorded yet.</p>
      ) : (
        <ul>
          {attempts.map((attempt, index) => (
            <li key={attempt.id} className={`attempt ${attempt.result}`}>
              <span className="attempt-number">#{attempts.length - index}</span>
              <span className="attempt-result">
                {attempt.result === "victory" ? "Victory" : `Failed — Phase ${attempt.phase_reached}`}
              </span>
              {attempt.result === "failed" && (
                <span className="attempt-cause">{getFailureLabel(boss, attempt)}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
