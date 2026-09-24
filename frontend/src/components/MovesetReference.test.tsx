import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MovesetReference from "./MovesetReference";
import { withLanguage } from "../i18n/testLanguage";
import type { Boss } from "../types";

const boss: Boss = {
  id: "isshin-sword-saint",
  name: "Isshin, the Sword Saint",
  name_zh: "剑圣 苇名一心",
  game: "sekiro",
  location: "Ashina Reservoir",
  location_zh: null,
  source_name: "Fextralife Sekiro Wiki",
  source_url: "https://sekiroshadowsdietwice.wiki.fextralife.com/Isshin,+the+Sword+Saint",
  phases: [
    {
      phase_number: 1,
      name: "Phase 1",
      name_zh: null,
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
          description_zh: "向下斩击放出一道剑气。",
          telegraph_zh: "刀柄上闪过一道光。",
          counter_zh: "弹开第一道剑气。",
          common_mistakes_zh: "防御剑气而不是弹开。",
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
          description_zh: null,
          telegraph_zh: null,
          counter_zh: null,
          common_mistakes_zh: null,
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

  it("shows only English in English mode", () => {
    render(<MovesetReference boss={boss} />);

    expect(screen.getByText("Dragon Flash")).toBeInTheDocument();
    expect(screen.queryByText("秘传·龙闪")).not.toBeInTheDocument();
    expect(screen.queryByText(/向下斩击/)).not.toBeInTheDocument();
  });

  it("shows only Chinese in Chinese mode, with one note about translations", () => {
    render(withLanguage(<MovesetReference boss={boss} />, "zh"));

    expect(screen.getByRole("heading", { name: "Boss 招式" })).toBeInTheDocument();
    expect(screen.getByText("向下斩击放出一道剑气。")).toBeInTheDocument();
    expect(screen.getByText("前摇：刀柄上闪过一道光。")).toBeInTheDocument();
    expect(screen.getByText("常见失误：防御剑气而不是弹开。")).toBeInTheDocument();
    expect(screen.queryByText("Dragon Flash")).not.toBeInTheDocument();
    expect(screen.queryByText(/Launches a force wave/)).not.toBeInTheDocument();
    expect(screen.getAllByText(/大多由本站译自/)).toHaveLength(1);
  });

  it("links a Chinese name taken from a wiki to its page, and leaves translations unlinked", () => {
    render(withLanguage(<MovesetReference boss={boss} />, "zh"));

    expect(screen.getByRole("link", { name: "秘传·龙闪" })).toHaveAttribute(
      "href",
      "https://wiki.biligame.com/sekiro/dragon-flash"
    );
    expect(screen.getByText("突刺")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "突刺" })).not.toBeInTheDocument();
  });
});
