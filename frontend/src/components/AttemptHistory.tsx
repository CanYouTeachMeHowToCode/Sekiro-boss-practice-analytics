import { useState } from "react";
import { formatPhase, useLanguage } from "../i18n/language";
import type { Attempt, Boss } from "../types";
import { getFailureLabel } from "../utils/moves";

interface AttemptHistoryProps {
  boss: Boss;
  attempts: Attempt[];
}

type ResultFilter = "all" | "victory" | "failed";

export default function AttemptHistory({ boss, attempts }: AttemptHistoryProps) {
  const { language, t } = useLanguage();
  const [resultFilter, setResultFilter] = useState<ResultFilter>("all");
  const numberedAttempts = attempts.map((attempt, index) => ({
    attempt,
    number: attempts.length - index,
  }));
  const visibleAttempts =
    resultFilter === "all"
      ? numberedAttempts
      : numberedAttempts.filter((item) => item.attempt.result === resultFilter);

  return (
    <section className="attempt-history">
      <h2>{t("history.heading")}</h2>

      <label>
        {t("history.filterLabel")}
        <select
          value={resultFilter}
          onChange={(e) => {
            const value = e.currentTarget.value;
            if (value === "all" || value === "victory" || value === "failed") {
              setResultFilter(value);
            }
          }}
        >
          <option value="all">{t("history.filterAll")}</option>
          <option value="victory">{t("result.victory")}</option>
          <option value="failed">{t("form.failed")}</option>
        </select>
      </label>

      {attempts.length === 0 ? (
        <p>{t("history.empty")}</p>
      ) : visibleAttempts.length === 0 ? (
        <p>{t("history.noMatch")}</p>
      ) : (
        <ul>
          {visibleAttempts.map(({ attempt, number }) => (
            <li key={attempt.id} className={`attempt ${attempt.result}`}>
              <span className="attempt-number">#{number}</span>
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
