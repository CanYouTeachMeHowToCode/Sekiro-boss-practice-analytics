import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import AnalyticsPanel from "./AnalyticsPanel";
import type { Boss, BossAnalytics } from "../types";

const boss: Boss = {
  id: "genichiro-ashina",
  name: "Genichiro Ashina",
  game: "sekiro",
  location: "Ashina Castle",
  phases: [
    {
      phase_number: 2,
      name: "Phase 2",
      moves: [
        { id: "floating-passage", name: "Floating Passage", move_type: "combo", description: null, counter: null },
      ],
    },
  ],
};

describe("AnalyticsPanel", () => {
  it("shows the main bottleneck phase and resolves the most common failure move to its name", () => {
    const analytics: BossAnalytics = {
      total_attempts: 5,
      defeated: false,
      best_phase: 2,
      main_bottleneck_phase: 2,
      most_common_failure_move: "floating-passage",
      failure_by_phase: { "2": 3 },
      failure_by_move: { "floating-passage": 3 },
    };

    render(<AnalyticsPanel boss={boss} analytics={analytics} />);

    const bottleneck = screen.getByText("Main Bottleneck").closest("div") as HTMLElement;
    expect(within(bottleneck).getByText("Phase 2")).toBeInTheDocument();

    const mostCommon = screen.getByText("Most Common Failure").closest("div") as HTMLElement;
    expect(within(mostCommon).getByText("Floating Passage")).toBeInTheDocument();
  });

  it("renders the failure-by-phase breakdown sorted by phase number, including phases with only unknown-cause failures", () => {
    const analytics: BossAnalytics = {
      total_attempts: 6,
      defeated: false,
      best_phase: 2,
      main_bottleneck_phase: 2,
      most_common_failure_move: null,
      failure_by_phase: { "2": 4, "1": 2 },
      failure_by_move: {},
    };

    render(<AnalyticsPanel boss={boss} analytics={analytics} />);

    const table = screen.getByRole("table", { name: /failure breakdown by phase/i });
    const cells = within(table).getAllByRole("cell").map((cell) => cell.textContent);

    expect(cells).toEqual(["Phase 1", "2", "Phase 2", "4"]);
    expect(screen.queryByRole("table", { name: /failure breakdown by move/i })).not.toBeInTheDocument();
  });

  it("renders the failure-by-move breakdown sorted by count, resolving move ids to names", () => {
    const analytics: BossAnalytics = {
      total_attempts: 4,
      defeated: false,
      best_phase: 2,
      main_bottleneck_phase: 2,
      most_common_failure_move: "floating-passage",
      failure_by_phase: { "2": 4 },
      failure_by_move: { "unknown-move": 1, "floating-passage": 3 },
    };

    render(<AnalyticsPanel boss={boss} analytics={analytics} />);

    const table = screen.getByRole("table", { name: /failure breakdown by move/i });
    const cells = within(table).getAllByRole("cell").map((cell) => cell.textContent);

    expect(cells).toEqual(["Floating Passage", "3", "unknown-move", "1"]);
  });

  it("shows a placeholder instead of empty stats when there are no attempts yet", () => {
    const analytics: BossAnalytics = {
      total_attempts: 0,
      defeated: false,
      best_phase: null,
      main_bottleneck_phase: null,
      most_common_failure_move: null,
      failure_by_phase: {},
      failure_by_move: {},
    };

    render(<AnalyticsPanel boss={boss} analytics={analytics} />);

    expect(screen.getByText(/record an attempt to start seeing analytics/i)).toBeInTheDocument();
  });
});
