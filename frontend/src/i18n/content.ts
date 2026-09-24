import type { Boss, BossMove, BossPhase, BossSummary } from "../types";
import type { Language } from "./messages";

/** The Chinese value in Chinese mode when it exists, otherwise the English one. */
function pick<T>(language: Language, english: T, chinese: T | null | undefined): T {
  return language === "zh" && chinese ? chinese : english;
}

type Named = Pick<BossSummary, "name" | "name_zh">;

export function bossName(boss: Named, language: Language): string {
  return pick(language, boss.name, boss.name_zh);
}

export function bossLocation(boss: Pick<Boss, "location" | "location_zh">, language: Language): string {
  return pick(language, boss.location, boss.location_zh);
}

export function phaseName(phase: Pick<BossPhase, "name" | "name_zh">, language: Language): string {
  return pick(language, phase.name, phase.name_zh);
}

export function moveName(move: Pick<BossMove, "name" | "name_zh">, language: Language): string {
  return pick(language, move.name, move.name_zh);
}

export type MoveTextField = "description" | "telegraph" | "counter" | "common_mistakes";

export function moveText(move: BossMove, field: MoveTextField, language: Language): string | null {
  return pick(language, move[field], move[`${field}_zh`]);
}
