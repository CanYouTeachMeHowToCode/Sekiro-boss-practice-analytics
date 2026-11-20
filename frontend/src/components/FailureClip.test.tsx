import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import FailureClip from "./FailureClip";
import { clipMarks } from "../utils/clipMarks";
import type { ClipMark } from "../utils/clipMarks";
import { withLanguage } from "../i18n/testLanguage";
import type { Language } from "../i18n/language";

/** The clip of a failure at 12.5 s, starting at 9.5 s and 5 s long; at() plays it to a moment. */
function renderClip(marks: ClipMark[], language: Language = "en") {
  const view = render(withLanguage(<FailureClip src="/clip.mp4" start={9.5} marks={marks} />, language));
  const video = view.container.querySelector("video") as HTMLVideoElement;
  let now = 0;
  Object.defineProperty(video, "currentTime", { get: () => now, set: (v: number) => (now = v), configurable: true });
  Object.defineProperty(video, "duration", { value: 5, configurable: true });
  const at = (seconds: number) => {
    now = seconds;
    fireEvent(video, new Event("timeupdate"));
  };
  return { ...view, video, at, now: () => now };
}

const own: ClipMark = { time_s: 12.5, types: ["damage"], own: true };

afterEach(() => {
  vi.restoreAllMocks();
});

describe("FailureClip", () => {
  it("shows the recording's own time over the clip, in red with the event at the failure's hit", () => {
    const { at } = renderClip([own]);
    const time = screen.getByTestId("clip-time");

    at(1);
    expect(time).toHaveTextContent("0:10.5");
    expect(time).not.toHaveClass("hit");

    at(3.1);
    expect(time).toHaveTextContent("0:12.6 · Hit");
    expect(time).toHaveClass("hit");

    at(4.5);
    expect(time).toHaveTextContent("0:14.0");
    expect(time).not.toHaveClass("hit");
  });

  it("does not turn red at another failure's hit", () => {
    const { at } = renderClip([own, { time_s: 10.2, types: ["damage"], own: false }]);
    at(0.7);
    expect(screen.getByTestId("clip-time")).toHaveTextContent("0:10.2");
    expect(screen.getByTestId("clip-time")).not.toHaveClass("hit");
  });

  it("lists the hits inside the clip once its length is known, and plays from a second before the one picked", async () => {
    const user = userEvent.setup();
    const play = vi.spyOn(window.HTMLMediaElement.prototype, "play").mockResolvedValue(undefined);
    const { container, video, now } = renderClip(
      [{ time_s: 3.0, types: ["damage"], own: false }, { time_s: 10.2, types: ["damage", "death"], own: false }, own],
      "zh"
    );
    expect(screen.queryByRole("list")).not.toBeInTheDocument();

    fireEvent(video, new Event("loadedmetadata"));

    const marks = within(screen.getByRole("list", { name: "片段里的受击" })).getAllByRole("button");
    // the hit at 3.0 s is before the clip
    expect(marks.map((b) => b.textContent)).toEqual(["扣血、死亡 0:10.2（另一次失败）", "扣血 0:12.5（这次失败）"]);
    expect(container.querySelector(".clip-ends")).toHaveTextContent("0:09.50:14.5");

    await user.click(marks[1]);
    expect(now()).toBeCloseTo(2.0);
    expect(play).toHaveBeenCalled();
  });
});

describe("clipMarks", () => {
  it("marks the failure's own events and every other failure's, a failure's events at one moment together", () => {
    const failures = [
      { id: "1", time_s: 42.1, type: "damage" as const, events: [{ type: "damage" as const, time_s: 42.1 }] },
      {
        id: "2",
        time_s: 44.8,
        type: "death" as const,
        events: [
          { type: "damage" as const, time_s: 44.8 },
          { type: "death" as const, time_s: 44.8 },
        ],
      },
      { id: "3", time_s: 90, type: "posture_break" as const, events: [] },
    ];
    expect(clipMarks(failures[1], failures)).toEqual([
      { time_s: 42.1, types: ["damage"], own: false },
      { time_s: 44.8, types: ["damage", "death"], own: true },
      { time_s: 90, types: ["posture_break"], own: false },
    ]);
  });
});
