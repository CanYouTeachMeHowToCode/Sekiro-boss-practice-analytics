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
        },
        {
          id: "thrust",
          name: "Thrust",
          move_type: "thrust",
          description: null,
          telegraph: null,
          counter: null,
          common_mistakes: null,
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
    expect(thrust.textContent).toBe("Thrust");
  });

  it("links to the boss's data source", () => {
    render(<MovesetReference boss={boss} />);

    expect(screen.getByRole("link", { name: "Fextralife Sekiro Wiki" })).toHaveAttribute("href", boss.source_url);
  });

  it("shows no source line when the boss has no source", () => {
    render(<MovesetReference boss={{ ...boss, source_name: null, source_url: null }} />);

    expect(screen.queryByText(/source:/i)).not.toBeInTheDocument();
  });
});
