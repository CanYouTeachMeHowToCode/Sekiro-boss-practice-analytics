import { describe, expect, it } from "vitest";
import { makeTranslate } from "../i18n/language";
import { getFailureLabel, getMoveName } from "./moves";

const t = makeTranslate("en");
import type { Attempt, Boss } from "../types";

const boss: Boss = {
  id: "genichiro-ashina",
  name: "Genichiro Ashina",
  game: "sekiro",
  location: "Ashina Castle",
  location_zh: null,
  phases: [
    {
      phase_number: 1,
      name: "Phase 1",
      name_zh: null,
      moves: [
        { id: "thrust-attack", name: "Thrust Attack", move_type: "thrust", description: null, telegraph: null, counter: null, common_mistakes: null, name_zh: null, name_zh_source: null, name_zh_source_url: null, description_zh: null, telegraph_zh: null, counter_zh: null, common_mistakes_zh: null },
      ],
    },
    {
      phase_number: 3,
      name: "Phase 3",
      name_zh: null,
      moves: [
        { id: "lightning-attack", name: "Lightning Attack", move_type: "lightning", description: null, telegraph: null, counter: null, common_mistakes: null, name_zh: null, name_zh_source: null, name_zh_source_url: null, description_zh: null, telegraph_zh: null, counter_zh: null, common_mistakes_zh: null },
      ],
    },
  ],
  name_zh: null,
  source_name: null,
  source_url: null,
};

function makeAttempt(overrides: Partial<Attempt>): Attempt {
  return {
    id: "attempt-001",
    boss_id: boss.id,
    timestamp: "2026-08-24T21:00:00Z",
    result: "failed",
    phase_reached: 1,
    failure_move_id: null,
    failure_category: null,
    notes: "",
    ...overrides,
  };
}

describe("getMoveName", () => {
  it("finds a move regardless of which phase it belongs to", () => {
    expect(getMoveName(boss, "lightning-attack")).toBe("Lightning Attack");
  });

  it("returns null when no move id is given", () => {
    expect(getMoveName(boss, null)).toBeNull();
  });

  it("falls back to the raw id when the move can't be found", () => {
    expect(getMoveName(boss, "unknown-move")).toBe("unknown-move");
  });
});

describe("getFailureLabel", () => {
  it("labels a victory", () => {
    expect(getFailureLabel(boss, makeAttempt({ result: "victory" }), t, "en")).toBe("Victory");
  });

  it("labels a known failure move by its display name", () => {
    expect(getFailureLabel(boss, makeAttempt({ failure_move_id: "thrust-attack" }), t, "en")).toBe("Thrust Attack");
  });

  it("labels a not_sure failure", () => {
    expect(getFailureLabel(boss, makeAttempt({ failure_category: "not_sure" }), t, "en")).toBe("Not Sure");
  });

  it("labels an other failure", () => {
    expect(getFailureLabel(boss, makeAttempt({ failure_category: "other" }), t, "en")).toBe("Other");
  });
});
