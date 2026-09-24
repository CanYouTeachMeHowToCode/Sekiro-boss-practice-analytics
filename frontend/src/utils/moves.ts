import { moveName } from "../i18n/content";
import type { Language, Translate } from "../i18n/language";
import type { Attempt, Boss } from "../types";

export function getMoveName(boss: Boss, moveId: string | null, language: Language = "en"): string | null {
  if (!moveId) return null;
  for (const phase of boss.phases) {
    const move = phase.moves.find((m) => m.id === moveId);
    if (move) return moveName(move, language);
  }
  return moveId;
}

export function getFailureLabel(boss: Boss, attempt: Attempt, t: Translate, language: Language): string {
  if (attempt.result === "victory") return t("result.victory");
  if (attempt.failure_move_id) return getMoveName(boss, attempt.failure_move_id, language) ?? attempt.failure_move_id;
  if (attempt.failure_category === "not_sure") return t("cause.notSure");
  if (attempt.failure_category === "other") return t("cause.other");
  return t("cause.unknown");
}
