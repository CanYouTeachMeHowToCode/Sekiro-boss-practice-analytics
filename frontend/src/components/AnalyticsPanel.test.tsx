import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import AnalyticsPanel from "./AnalyticsPanel";
import type { Boss, BossAnalytics, RecentAnalytics } from "../types";

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
        { id: "perilous-thrust", name: "Perilous Thrust", move_type: "thrust", description: null, telegraph: null, counter: null, common_mistakes: null, name_zh: null, name_zh_source: null, name_zh_source_url: null, description_zh: null, telegraph_zh: null, counter_zh: null, common_mistakes_zh: null },
      ],
    },
    {
      phase_number: 2,
      name: "Phase 2",
      name_zh: null,
      moves: [
        { id: "floating-passage", name: "Floating Passage", move_type: "combo", description: null, telegraph: null, counter: null, common_mistakes: null, name_zh: null, name_zh_source: null, name_zh_source_url: null, description_zh: null, telegraph_zh: null, counter_zh: null, common_mistakes_zh: null },
      ],
    },
  ],
  name_zh: null,
  source_name: null,
  source_url: null,
};

function makeAnalytics(
  allTime: Pick<BossAnalytics, "total_attempts" | "failure_by_phase" | "failure_by_move">,
  recent: Partial<RecentAnalytics> = {}
): BossAnalytics {
  return {
    defeated: false,
    best_phase: 2,
    main_bottleneck_phase: null,
    most_common_failure_move: null,
    attempts_until_first_victory: null,
    ...allTime,
    recent: {
      window_size: 10,
      total_attempts: allTime.total_attempts,
      main_bottleneck_phase: null,
      most_common_failure_move: null,
      failure_by_phase: allTime.failure_by_phase,
      failure_by_move: allTime.failure_by_move,
      ...recent,
    },
  };
}

function summaryValues(heading: string) {
  const card = screen.getByRole("heading", { name: heading }).closest("div") as HTMLElement;
  return within(card)
    .getAllByRole("definition")
    .map((dd) => dd.textContent);
}

function tableCells(name: RegExp) {
  const table = screen.getByRole("table", { name });
  return within(table)
    .getAllByRole("row")
    .map((row) => within(row).queryAllByRole("cell").map((cell) => cell.textContent))
    .filter((cells) => cells.length > 0);
}

describe("AnalyticsPanel", () => {
  it("shows the all-time and recent conclusions side by side", () => {
    render(
      <AnalyticsPanel
        boss={boss}
        analytics={makeAnalytics(
          { total_attempts: 13, failure_by_phase: { "1": 9, "2": 4 }, failure_by_move: { "perilous-thrust": 9, "floating-passage": 4 } },
          { failure_by_phase: { "1": 1, "2": 4 }, failure_by_move: { "perilous-thrust": 1, "floating-passage": 4 } }
        )}
      />
    );

    expect(summaryValues("Main Bottleneck")).toEqual(["Phase 1", "Phase 2"]);
    expect(summaryValues("Most Common Failure")).toEqual(["Perilous Thrust", "Floating Passage"]);
  });

  it("shows ties instead of picking one", () => {
    render(
      <AnalyticsPanel
        boss={boss}
        analytics={makeAnalytics({
          total_attempts: 2,
          failure_by_phase: { "1": 1, "2": 1 },
          failure_by_move: { "perilous-thrust": 1, "floating-passage": 1 },
        })}
      />
    );

    expect(summaryValues("Main Bottleneck")[0]).toBe("Phase 1, Phase 2 (tied)");
    expect(summaryValues("Most Common Failure")[0]).toBe("Perilous Thrust, Floating Passage (tied)");
  });

  it("compares failures by phase, filling phases absent from the recent window with 0", () => {
    render(
      <AnalyticsPanel
        boss={boss}
        analytics={makeAnalytics(
          { total_attempts: 12, failure_by_phase: { "2": 4, "1": 8 }, failure_by_move: {} },
          { failure_by_phase: { "2": 4 } }
        )}
      />
    );

    expect(tableCells(/failure breakdown by phase/i)).toEqual([
      ["Phase 1", "8", "0"],
      ["Phase 2", "4", "4"],
    ]);
    expect(screen.queryByRole("table", { name: /failure breakdown by move/i })).not.toBeInTheDocument();
  });

  it("compares failures by move, sorted by all-time count and resolved to names", () => {
    render(
      <AnalyticsPanel
        boss={boss}
        analytics={makeAnalytics(
          { total_attempts: 4, failure_by_phase: { "2": 4 }, failure_by_move: { "unknown-move": 1, "floating-passage": 3 } },
          { failure_by_move: { "floating-passage": 2 } }
        )}
      />
    );

    expect(tableCells(/failure breakdown by move/i)).toEqual([
      ["Floating Passage", "3", "2"],
      ["unknown-move", "1", "0"],
    ]);
  });

  it("labels the recent column with how many attempts it actually covers", () => {
    const { rerender } = render(
      <AnalyticsPanel
        boss={boss}
        analytics={makeAnalytics({ total_attempts: 6, failure_by_phase: { "1": 6 }, failure_by_move: {} }, { total_attempts: 6 })}
      />
    );
    expect(screen.getAllByText("Last 6 (all so far)").length).toBeGreaterThan(0);

    rerender(
      <AnalyticsPanel
        boss={boss}
        analytics={makeAnalytics({ total_attempts: 25, failure_by_phase: { "1": 25 }, failure_by_move: {} }, { total_attempts: 10 })}
      />
    );
    expect(screen.getAllByText("Last 10").length).toBeGreaterThan(0);
  });

  it("shows a placeholder instead of empty stats when there are no attempts yet", () => {
    render(
      <AnalyticsPanel boss={boss} analytics={makeAnalytics({ total_attempts: 0, failure_by_phase: {}, failure_by_move: {} })} />
    );

    expect(screen.getByText(/record an attempt to start seeing analytics/i)).toBeInTheDocument();
  });
});
