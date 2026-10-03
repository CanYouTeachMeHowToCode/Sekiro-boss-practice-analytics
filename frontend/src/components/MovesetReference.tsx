import { moveName, moveText, phaseName } from "../i18n/content";
import { useLanguage } from "../i18n/language";
import type { Boss, BossMove } from "../types";

function MoveTitle({ move }: { move: BossMove }) {
  const { language, t } = useLanguage();
  const name = moveName(move, language);

  // In Chinese, a name taken from a Chinese wiki links to that page.
  if (language === "zh" && move.name_zh_source === "wiki" && move.name_zh_source_url) {
    return (
      <strong>
        <a href={move.name_zh_source_url} target="_blank" rel="noopener noreferrer" title={t("moveset.wikiNameTitle")}>
          {name}
        </a>
      </strong>
    );
  }
  return <strong>{name}</strong>;
}

export default function MovesetReference({ boss }: { boss: Boss }) {
  const { language, t } = useLanguage();

  return (
    <section className="moveset-reference">
      <h2>{t("moveset.heading")}</h2>
      {language === "zh" && <p className="moveset-note">{t("moveset.translationNote")}</p>}

      {boss.phases.map((phase) => (
        <div key={phase.phase_number} className="moveset-phase">
          <h3>{phaseName(phase, language)}</h3>
          <ul>
            {phase.moves.map((move) => {
              const description = moveText(move, "description", language);
              const telegraph = moveText(move, "telegraph", language);
              const counter = moveText(move, "counter", language);
              const mistakes = moveText(move, "common_mistakes", language);
              return (
                <li key={move.id}>
                  <MoveTitle move={move} />
                  {description && <p>{description}</p>}
                  {telegraph && <p className="telegraph">{t("moveset.telegraph", { text: telegraph })}</p>}
                  {counter && <p className="counter">{t("moveset.counter", { text: counter })}</p>}
                  {mistakes && <p className="common-mistakes">{t("moveset.commonMistake", { text: mistakes })}</p>}
                </li>
              );
            })}
          </ul>
        </div>
      ))}

      {boss.source_url && (
        <p className="moveset-source">
          {t("moveset.source")}{" "}
          <a href={boss.source_url} target="_blank" rel="noopener noreferrer">
            {boss.source_name ?? boss.source_url}
          </a>
        </p>
      )}
    </section>
  );
}
