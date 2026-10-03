import { formatPhase, useLanguage } from "../i18n/language";
import type { Attempt, Boss } from "../types";
import { getFailureLabel } from "../utils/moves";

interface AttemptHistoryProps {
  boss: Boss;
  attempts: Attempt[];
}

export default function AttemptHistory({ boss, attempts }: AttemptHistoryProps) {
  const { language, t } = useLanguage();

  return (
    <section className="attempt-history">
      <h2>{t("history.heading")}</h2>

      {attempts.length === 0 ? (
        <p>{t("history.empty")}</p>
      ) : (
        <ul>
          {attempts.map((attempt, index) => (
            <li key={attempt.id} className={`attempt ${attempt.result}`}>
              <span className="attempt-number">#{attempts.length - index}</span>
              <span className="attempt-result">
                {attempt.result === "victory"
                  ? t("result.victory")
                  : t("result.failedAt", { phase: formatPhase(attempt.phase_reached, language) })}
              </span>
              {attempt.result === "failed" && (
                <span className="attempt-cause">{getFailureLabel(boss, attempt, t, language)}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
