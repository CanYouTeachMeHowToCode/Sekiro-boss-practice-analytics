import type { Boss, BossMove, Recording, RecordingReport } from "../types";

/** Recordings and a small Genichiro moveset for the recording pages' tests. */
export function makeRecording(overrides: Partial<Recording> = {}): Recording {
  return {
    id: "7",
    boss_id: "genichiro-ashina",
    filename: "genichiro.mp4",
    status: "done",
    reject_code: null,
    progress: 1,
    size_bytes: 1_500_000_000,
    duration_s: 307,
    width: 2560,
    height: 1440,
    low_resolution: false,
    created_at: "2026-11-17T10:30:00Z",
    processed_at: "2026-11-17T10:45:00Z",
    ...overrides,
  };
}

function move(id: string, name: string, nameZh: string): BossMove {
  return {
    id,
    name,
    name_zh: nameZh,
    move_type: "attack",
    description: null,
    telegraph: null,
    counter: null,
    common_mistakes: null,
    description_zh: null,
    telegraph_zh: null,
    counter_zh: null,
    common_mistakes_zh: null,
    source_name: null,
    source_url: null,
    name_zh_source: "translation",
    name_zh_source_url: null,
  };
}

export const genichiro: Boss = {
  id: "genichiro-ashina",
  name: "Genichiro Ashina",
  name_zh: "苇名弦一郎",
  game: "sekiro",
  location: "Ashina Castle",
  location_zh: "苇名城",
  source_name: null,
  source_url: null,
  phases: [
    {
      phase_number: 1,
      name: "Phase 1",
      name_zh: "第一阶段",
      moves: [
        move("floating-passage", "Floating Passage", "绝技·飞渡浮舟"),
        move("hawk-shot", "Hawk Shot", "鹰射"),
        move("counter-slash", "Counter Slash", "强弹反斩"),
      ],
    },
    {
      phase_number: 3,
      name: "Phase 3",
      name_zh: "第三阶段",
      moves: [move("lightning-of-tomoe-smash", "Lightning of Tomoe Smash", "巴之雷·砸击")],
    },
  ],
};

/** Four failures: two sure ones of Floating Passage (a hit, and a hit that killed), one sure Hawk Shot, one unsure. */
export function makeReport(recording: Partial<Recording> = {}): RecordingReport {
  return {
    recording: makeRecording(recording),
    failures: [
      {
        id: "1",
        time_s: 12.5,
        type: "damage",
        phase: 1,
        sure: true,
        move_id: "floating-passage",
        candidates: [{ move_id: "floating-passage", score: 0.21 }],
        events: [{ type: "damage", time_s: 12.5 }],
        has_clip: true,
      },
      {
        id: "2",
        time_s: 40.04,
        type: "death",
        phase: 1,
        sure: true,
        move_id: "floating-passage",
        candidates: [{ move_id: "floating-passage", score: 0.25 }],
        events: [
          { type: "damage", time_s: 40.04 },
          { type: "death", time_s: 40.2 },
        ],
        has_clip: false,
      },
      {
        id: "3",
        time_s: 70,
        type: "damage",
        phase: 1,
        sure: true,
        move_id: "hawk-shot",
        candidates: [{ move_id: "hawk-shot", score: 0.3 }],
        events: [{ type: "damage", time_s: 70 }],
        has_clip: false,
      },
      {
        id: "4",
        time_s: 283.8,
        type: "posture_break",
        phase: 3,
        sure: false,
        move_id: null,
        candidates: [
          { move_id: "counter-slash", score: 0.12 },
          { move_id: "hawk-shot", score: 0.11 },
          { move_id: "lightning-of-tomoe-smash", score: 0.1 },
          { move_id: "floating-passage", score: 0.09 },
        ],
        events: [{ type: "posture_break", time_s: 283.8 }],
        has_clip: false,
      },
    ],
    by_move: [
      { move_id: "floating-passage", damage: 1, posture_break: 0, death: 1, total: 2 },
      { move_id: "hawk-shot", damage: 1, posture_break: 0, death: 0, total: 1 },
    ],
    uncertain: 1,
  };
}
