import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import SekiroDashboardPage from "./SekiroDashboardPage";
import * as sekiroApi from "../api/sekiro";
import type { BossComparisonRow, SekiroAnalytics } from "../types";
import { withLanguage } from "../i18n/testLanguage";

vi.mock("../api/sekiro");

function row(overrides: Partial<BossComparisonRow>): BossComparisonRow {
  return {
    id: "owl-father",
    name: "Owl (Father)",
    name_zh: "义父",
    total_phases: 2,
    attempts: 0,
    best_phase: null,
    defeated: false,
    attempts_until_first_victory: null,
    last_attempt_at: null,
    ...overrides,
  };
}

const bosses = [
  row({ id: "genichiro-ashina", name: "Genichiro Ashina", name_zh: "苇名弦一郎", total_phases: 3, attempts: 3, best_phase: 3, defeated: true, attempts_until_first_victory: 3 }),
  row({ id: "owl-father", attempts: 3, best_phase: 2 }),
  row({ id: "guardian-ape", name: "Guardian Ape", name_zh: "狮子猿" }),
];

const analytics: SekiroAnalytics = {
  total_bosses: 3,
  bosses_attempted: 2,
  bosses_defeated: 1,
  total_attempts: 6,
  most_practiced_bosses: ["genichiro-ashina", "owl-father"],
  most_attempts_to_defeat: 3,
  bosses_requiring_most_attempts: ["genichiro-ashina"],
  recent_window_days: 7,
  attempts_in_recent_window: 4,
  recent_attempts: [
    {
      attempt_id: "12",
      boss_id: "owl-father",
      boss_name: "Owl (Father)",
      boss_name_zh: null,
      timestamp: "2026-09-22T23:00:00Z",
      result: "failed",
      phase_reached: 2,
      failure_move_id: "owl-teleport",
      failure_move_name: "Owl Teleport",
      failure_move_name_zh: "枭之瞬移",
      failure_category: null,
    },
    {
      attempt_id: "11",
      boss_id: "genichiro-ashina",
      boss_name: "Genichiro Ashina",
      boss_name_zh: null,
      timestamp: "2026-09-22T22:00:00Z",
      result: "victory",
      phase_reached: 3,
      failure_move_id: null,
      failure_move_name: null,
      failure_move_name_zh: null,
      failure_category: null,
    },
  ],
  bosses,
};

function renderPage() {
  return render(
    <MemoryRouter>
      <SekiroDashboardPage />
    </MemoryRouter>
  );
}

function statValue(heading: string) {
  return (screen.getByRole("heading", { name: heading }).closest("div") as HTMLElement).querySelector("p")?.textContent;
}

describe("SekiroDashboardPage", () => {
  it("shows the overall practice numbers", async () => {
    vi.mocked(sekiroApi.getSekiroAnalytics).mockResolvedValue(analytics);
    renderPage();

    await screen.findByRole("heading", { name: "Sekiro Practice Dashboard" });
    expect(statValue("Bosses Attempted")).toBe("2 / 3");
    expect(statValue("Bosses Defeated")).toBe("1");
    expect(statValue("Total Attempts")).toBe("6");
    expect(statValue("Last 7 Days")).toBe("4");
  });

  it("names the most practiced bosses as a tie and the boss requiring most attempts", async () => {
    vi.mocked(sekiroApi.getSekiroAnalytics).mockResolvedValue(analytics);
    renderPage();

    await screen.findByRole("heading", { name: "Sekiro Practice Dashboard" });
    expect(statValue("Most Practiced Boss")).toBe("Genichiro Ashina, Owl (Father) (tied) — 3 attempts");
    expect(statValue("Boss Requiring Most Attempts to Defeat")).toBe("Genichiro Ashina — 3 attempts");
  });

  it("compares every boss, linking to its dashboard", async () => {
    vi.mocked(sekiroApi.getSekiroAnalytics).mockResolvedValue(analytics);
    renderPage();

    const table = await screen.findByRole("table");
    const rows = within(table)
      .getAllByRole("row")
      .slice(1)
      .map((r) => within(r).getAllByRole("cell").map((c) => c.textContent));

    expect(rows).toEqual([
      ["Genichiro Ashina", "3", "Victory", "Yes", "Attempt #3"],
      ["Owl (Father)", "3", "Phase 2 / 2", "No", "—"],
      ["Guardian Ape", "0", "—", "No", "—"],
    ]);
    expect(within(table).getByRole("link", { name: "Guardian Ape" })).toHaveAttribute("href", "/bosses/guardian-ape");
  });

  it("lists recent attempts across bosses", async () => {
    vi.mocked(sekiroApi.getSekiroAnalytics).mockResolvedValue(analytics);
    renderPage();

    const section = (await screen.findByRole("heading", { name: "Recent Practice" })).closest("section") as HTMLElement;
    const items = within(section).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("Owl (Father)");
    expect(items[0]).toHaveTextContent("Failed — Phase 2");
    expect(items[0]).toHaveTextContent("Owl Teleport");
    expect(items[1]).toHaveTextContent("Victory");
  });

  it("shows empty states before any attempts", async () => {
    vi.mocked(sekiroApi.getSekiroAnalytics).mockResolvedValue({
      ...analytics,
      bosses_attempted: 0,
      bosses_defeated: 0,
      total_attempts: 0,
      most_practiced_bosses: [],
      most_attempts_to_defeat: null,
      bosses_requiring_most_attempts: [],
      attempts_in_recent_window: 0,
      recent_attempts: [],
      bosses: bosses.map((b) => row({ id: b.id, name: b.name, name_zh: b.name_zh })),
    });
    renderPage();

    await screen.findByRole("heading", { name: "Sekiro Practice Dashboard" });
    expect(statValue("Most Practiced Boss")).toBe("No attempts yet");
    expect(statValue("Boss Requiring Most Attempts to Defeat")).toBe("No boss defeated yet");
    expect(screen.getByText(/no attempts recorded yet/i)).toBeInTheDocument();
  });

  it("shows an error when the analytics fail to load", async () => {
    vi.mocked(sekiroApi.getSekiroAnalytics).mockRejectedValue(new Error("network"));
    renderPage();

    expect(await screen.findByRole("alert")).toHaveTextContent(/failed to load/i);
  });

  it("shows the comparison in Chinese in Chinese mode", async () => {
    vi.mocked(sekiroApi.getSekiroAnalytics).mockResolvedValue(analytics);
    render(withLanguage(<MemoryRouter><SekiroDashboardPage /></MemoryRouter>, "zh"));

    const table = await screen.findByRole("table");
    const rows = within(table)
      .getAllByRole("row")
      .slice(1)
      .map((r) => within(r).getAllByRole("cell").map((c) => c.textContent));

    expect(screen.getByRole("heading", { name: "只狼练习总览" })).toBeInTheDocument();
    expect(rows).toEqual([
      ["苇名弦一郎", "3", "胜利", "是", "第 3 次"],
      ["义父", "3", "第 2 / 2 阶段", "否", "—"],
      ["狮子猿", "0", "—", "否", "—"],
    ]);
  });
});
