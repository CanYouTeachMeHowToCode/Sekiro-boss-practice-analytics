import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MovesetReference from "./MovesetReference";
import type { Boss } from "../types";

const boss: Boss = {
  id: "isshin-sword-saint",
  name: "Isshin, the Sword Saint",
  name_zh: "剑圣 苇名一心",
  game: "sekiro",
  location: "Ashina Reservoir",
  source_name: "Fextralife Sekiro Wiki",
  source_url: "https://sekiroshadowsdietwice.wiki.fextralife.com/Isshin,+the+Sword+Saint",
  phases: [
    {
      phase_number: 1,
      name: "Phase 1",
      moves: [
        {
          id: "dragon-flash",
          name: "Dragon Flash",
          move_type: "ranged",
          description: "Launches a force wave.",
          telegraph: "A glint shows on the hilt.",
          counter: "Deflect the first wave.",
          common_mistakes: "Blocking the waves instead of deflecting them.",
          name_zh: "秘传·龙闪",
          name_zh_source: "wiki",
          name_zh_source_url: "https://wiki.biligame.com/sekiro/dragon-flash",
        },
        {
          id: "thrust",
          name: "Thrust",
          move_type: "thrust",
          description: null,
          telegraph: null,
          counter: null,
          common_mistakes: null,
          name_zh: "突刺",
          name_zh_source: "translation",
          name_zh_source_url: null,
        },
      ],
    },
  ],
};

describe("MovesetReference", () => {
  it("shows the telegraph, counter, and common mistake for a move", () => {
    render(<MovesetReference boss={boss} />);

    expect(screen.getByText("Telegraph: A glint shows on the hilt.")).toBeInTheDocument();
    expect(screen.getByText("Counter: Deflect the first wave.")).toBeInTheDocument();
    expect(screen.getByText("Common mistake: Blocking the waves instead of deflecting them.")).toBeInTheDocument();
  });

  it("omits fields a move doesn't have", () => {
    render(<MovesetReference boss={boss} />);

    const thrust = screen.getByText("Thrust").closest("li") as HTMLElement;
    // Only the names: no description, telegraph, counter or common-mistake paragraphs.
    expect(thrust.querySelectorAll("p")).toHaveLength(0);
    expect(thrust.textContent).toBe("Thrust突刺译名");
  });

  it("links to the boss's data source", () => {
    render(<MovesetReference boss={boss} />);

    expect(screen.getByRole("link", { name: "Fextralife Sekiro Wiki" })).toHaveAttribute("href", boss.source_url);
  });

  it("shows no source line when the boss has no source", () => {
    render(<MovesetReference boss={{ ...boss, source_name: null, source_url: null }} />);

    expect(screen.queryByText(/source:/i)).not.toBeInTheDocument();
  });

  it("links Chinese names taken from a wiki to their source page", () => {
    render(<MovesetReference boss={boss} />);

    const link = screen.getByRole("link", { name: "秘传·龙闪" });
    expect(link).toHaveAttribute("href", "https://wiki.biligame.com/sekiro/dragon-flash");
  });

  it("marks translated Chinese names as translations", () => {
    render(<MovesetReference boss={boss} />);

    expect(screen.getByText("突刺")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "突刺" })).not.toBeInTheDocument();
    expect(screen.getByTitle(/not an official in-game name/)).toHaveTextContent("译名");
  });
});
