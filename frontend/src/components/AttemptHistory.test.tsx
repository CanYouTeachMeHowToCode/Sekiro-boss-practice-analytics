import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import AttemptHistory from "./AttemptHistory";
import { withLanguage } from "../i18n/testLanguage";
import type { Attempt, Boss } from "../types";

const boss: Boss = {
  id: "genichiro-ashina",
  name: "Genichiro Ashina",
  game: "sekiro",
  location: "Ashina Castle",
  location_zh: null,
  phases: [
    {
      phase_number: 2,
      name: "Phase 2",
      name_zh: null,
      moves: [
        { id: "floating-passage", name: "Floating Passage", move_type: "combo", description: null, telegraph: null, counter: null, common_mistakes: null, name_zh: null, name_zh_source: null, name_zh_source_url: null, description_zh: null, telegraph_zh: null, counter_zh: null, common_mistakes_zh: null, source_name: null, source_url: null },
      ],
    },
  ],
  name_zh: null,
  source_name: null,
  source_url: null,
};

const attempts: Attempt[] = [
  {
    id: "attempt-002",
    boss_id: boss.id,
    timestamp: "2026-08-24T21:15:00Z",
    result: "failed",
    phase_reached: 2,
    failure_move_id: "floating-passage",
    failure_category: null,
    notes: "",
  },
  {
    id: "attempt-001",
    boss_id: boss.id,
    timestamp: "2026-08-24T21:00:00Z",
    result: "victory",
    phase_reached: 3,
    failure_move_id: null,
    failure_category: null,
    notes: "",
  },
];

describe("AttemptHistory", () => {
  it("shows the failure move's display name and phase for a failed attempt", () => {
    render(<AttemptHistory boss={boss} attempts={attempts} />);

    expect(screen.getByText("Floating Passage")).toBeInTheDocument();
    expect(screen.getByText(/failed — phase 2/i)).toBeInTheDocument();
  });

  it("shows Victory without a failure cause for a successful attempt", () => {
    render(<AttemptHistory boss={boss} attempts={attempts} />);

    expect(within(screen.getByRole("list")).getByText("Victory")).toBeInTheDocument();
  });

  it("shows a placeholder and no filter when there is no history yet", () => {
    render(<AttemptHistory boss={boss} attempts={[]} />);

    expect(screen.getByText(/no attempts recorded yet/i)).toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });
});

function makeAttempt(id: string, result: Attempt["result"]): Attempt {
  return {
    id,
    boss_id: boss.id,
    timestamp: "2026-08-24T21:00:00Z",
    result,
    phase_reached: 2,
    failure_move_id: null,
    failure_category: result === "failed" ? "not_sure" : null,
    notes: "",
  };
}

// Newest first, as the dashboard passes them: #4 failed, #3 victory, #2 failed, #1 failed.
const mixedAttempts = [
  makeAttempt("attempt-004", "failed"),
  makeAttempt("attempt-003", "victory"),
  makeAttempt("attempt-002", "failed"),
  makeAttempt("attempt-001", "failed"),
];

function shownNumbers(): (string | null)[] {
  return within(screen.getByRole("list"))
    .getAllByText(/^#\d+$/)
    .map((element) => element.textContent);
}

describe("AttemptHistory result filter", () => {
  it("shows every attempt until a result is chosen", () => {
    render(<AttemptHistory boss={boss} attempts={mixedAttempts} />);

    const filter = screen.getByRole("combobox", { name: "Filter by result" });
    expect(filter).toHaveValue("all");
    expect(within(filter).getAllByRole("option").map((option) => option.textContent)).toEqual([
      "All",
      "Victory",
      "Failed",
    ]);
    expect(shownNumbers()).toEqual(["#4", "#3", "#2", "#1"]);
  });

  it("shows only the chosen result and keeps each attempt's original number", async () => {
    const user = userEvent.setup();
    render(<AttemptHistory boss={boss} attempts={mixedAttempts} />);
    const filter = screen.getByRole("combobox", { name: "Filter by result" });

    await user.selectOptions(filter, "victory");
    expect(shownNumbers()).toEqual(["#3"]);

    await user.selectOptions(filter, "failed");
    expect(shownNumbers()).toEqual(["#4", "#2", "#1"]);

    await user.selectOptions(filter, "all");
    expect(shownNumbers()).toEqual(["#4", "#3", "#2", "#1"]);
  });

  it("says so when no attempt has the chosen result", async () => {
    const user = userEvent.setup();
    render(<AttemptHistory boss={boss} attempts={[makeAttempt("attempt-001", "failed")]} />);

    await user.selectOptions(screen.getByRole("combobox", { name: "Filter by result" }), "victory");

    expect(screen.getByText("No attempts match this filter.")).toBeInTheDocument();
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("names the filter and its options in Chinese on the Chinese page", () => {
    render(withLanguage(<AttemptHistory boss={boss} attempts={mixedAttempts} />, "zh"));

    const filter = screen.getByRole("combobox", { name: "结果筛选" });
    expect(within(filter).getAllByRole("option").map((option) => option.textContent)).toEqual([
      "全部",
      "胜利",
      "失败",
    ]);
  });
});
