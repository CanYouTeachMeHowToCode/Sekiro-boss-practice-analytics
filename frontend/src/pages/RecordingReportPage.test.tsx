import { act, cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import RecordingReportPage from "./RecordingReportPage";
import * as bossesApi from "../api/bosses";
import * as recordingsApi from "../api/recordings";
import { ApiError } from "../api/client";
import { genichiro, makeReport } from "../api/testRecordings";
import { withAuth } from "../auth/testAuth";
import type { AuthState } from "../auth/authContext";
import { withLanguage } from "../i18n/testLanguage";
import type { Language } from "../i18n/language";
import { REPORT_POLL_MS } from "../utils/recordings";

vi.mock("../api/bosses");
vi.mock("../api/recordings", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/recordings")>()),
  getRecordingReport: vi.fn(),
  deleteRecording: vi.fn(),
}));

function renderReport(language: Language = "en", auth: Partial<AuthState> = {}) {
  return render(
    withAuth(
      withLanguage(
        <MemoryRouter initialEntries={["/recordings/7"]}>
          <Routes>
            <Route path="/recordings/:recordingId" element={<RecordingReportPage />} />
            <Route path="/recordings" element={<p>recording list</p>} />
          </Routes>
        </MemoryRouter>,
        language
      ),
      auth
    )
  );
}

describe("RecordingReportPage", () => {
  beforeEach(() => {
    vi.mocked(bossesApi.getBossById).mockResolvedValue(genichiro);
  });

  afterEach(() => {
    vi.useRealTimers();
    // unmount first: a pending effect that calls a mocked API must run before the mocks are restored
    cleanup();
    vi.restoreAllMocks();
  });

  it("counts the failures per move from the sure answers and lists every failure", async () => {
    vi.mocked(recordingsApi.getRecordingReport).mockResolvedValue(makeReport());

    renderReport();

    expect(await screen.findByRole("heading", { name: "genichiro.mp4" })).toBeInTheDocument();
    expect(screen.getByText("2560×1440")).toBeInTheDocument();
    expect(screen.getByText("5:07")).toBeInTheDocument();
    // failure counts only, and no rates anywhere (CLAUDE.md 7.2); the table title says they are counts
    expect(screen.queryByText(/success rate/i)).not.toBeInTheDocument();
    const table = screen.getByRole("table");
    await waitFor(() => expect(within(table).getByText("Floating Passage")).toBeInTheDocument());
    const rows = within(table).getAllByRole("row").map((row) => row.textContent);
    expect(rows).toEqual(["MoveHitsPosture BreaksDeathsTotal", "Floating Passage1012", "Hawk Shot1001"]);
    expect(screen.getByText("Failures whose move is unsure, not counted in this table: 1")).toBeInTheDocument();

    const items = within(screen.getByRole("list")).getAllByRole("listitem");
    expect(items).toHaveLength(4);
    expect(within(items[1]).getByText("Events: Hit 0:40.0, Death 0:40.2")).toBeInTheDocument();
    // an unsure failure names its first three candidates, not a move
    expect(
      within(items[3]).getByText("Move unsure, possibly Counter Slash, Hawk Shot or Lightning of Tomoe Smash")
    ).toBeInTheDocument();
    expect(screen.queryByText(/below 1080p/)).not.toBeInTheDocument();
  });

  it("plays a failure's clip on request", async () => {
    const user = userEvent.setup();
    vi.mocked(recordingsApi.getRecordingReport).mockResolvedValue(makeReport());
    const { container } = renderReport();

    await user.click(await screen.findByRole("button", { name: "Play clip" }));

    expect(container.querySelector("video")?.getAttribute("src")).toBe("/api/recordings/7/failures/1/clip");
    expect(screen.getAllByRole("button", { name: /clip/ })).toHaveLength(1);
  });

  it("says in Chinese that move recognition is less sure below 1080p", async () => {
    vi.mocked(recordingsApi.getRecordingReport).mockResolvedValue(
      makeReport({ width: 1280, height: 720, low_resolution: true })
    );

    renderReport("zh");

    expect(
      await screen.findByText(
        '这段录像低于 1080p，招式识别的把握较低，更多失败会显示"招式不确定"。下次建议用 1080p 或更高分辨率录制。'
      )
    ).toBeInTheDocument();
    expect(await screen.findByText("招式不确定，可能是强弹反斩、鹰射或巴之雷·砸击")).toBeInTheDocument();
    expect(screen.getByText("按招式统计的失败次数")).toBeInTheDocument();
  });

  it("explains why a recording was rejected", async () => {
    vi.mocked(recordingsApi.getRecordingReport).mockResolvedValue({
      ...makeReport({ status: "rejected", reject_code: "too_long", progress: 0 }),
      failures: [],
      by_move: [],
      uncertain: 0,
    });

    renderReport();

    expect(await screen.findByText("This recording was not analysed.")).toBeInTheDocument();
    expect(screen.getByText("It is longer than 10 minutes.")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("follows the analysis until the report is ready", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const processing = { ...makeReport({ status: "processing", progress: 0.42 }), failures: [], by_move: [], uncertain: 0 };
    vi.mocked(recordingsApi.getRecordingReport).mockResolvedValueOnce(processing).mockResolvedValueOnce(makeReport());

    renderReport();

    expect(await screen.findByText("Analysing: 42%")).toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(REPORT_POLL_MS));
    expect(await screen.findByRole("table")).toBeInTheDocument();
    expect(recordingsApi.getRecordingReport).toHaveBeenCalledTimes(2);
  });

  it("says a 30 fps report is for reference only, in both languages, and nothing at 60 fps", async () => {
    vi.mocked(recordingsApi.getRecordingReport).mockResolvedValue(makeReport({ fps: 30, unvalidated_frame_rate: true }));
    const { unmount } = renderReport("zh");
    expect(
      await screen.findByText("这段录像是 30 帧，结果仅供参考：目前只有 60 帧录像的识别准确度经过验证。建议下次用 60 帧录制。")
    ).toBeInTheDocument();
    unmount();

    renderReport("en");
    expect(await screen.findByText(/This recording is 30 fps, so treat these results as a guide only/)).toBeInTheDocument();
  });

  it("shows no frame-rate note for a 60 fps recording", async () => {
    vi.mocked(recordingsApi.getRecordingReport).mockResolvedValue(makeReport());
    renderReport();
    expect(await screen.findByRole("heading", { name: "genichiro.mp4" })).toBeInTheDocument();
    expect(screen.queryByText(/as a guide only/)).not.toBeInTheDocument();
  });

  it("names no move for an unsure failure whose candidates could not be compared", async () => {
    const report = makeReport();
    report.failures[3].candidates = [
      { move_id: "counter-slash", score: -1 },
      { move_id: "hawk-shot", score: -1 },
    ];
    vi.mocked(recordingsApi.getRecordingReport).mockResolvedValue(report);
    renderReport();

    const items = await screen.findAllByRole("listitem");
    expect(within(items[3]).getByText("Move unsure")).toBeInTheDocument();
    // the owner sees no scores
    expect(screen.queryByText(/^Scores:/)).not.toBeInTheDocument();
  });

  it("names only the candidates that could be compared", async () => {
    const report = makeReport();
    report.failures[3].candidates = [
      { move_id: "counter-slash", score: 0.12 },
      { move_id: "hawk-shot", score: -1 },
    ];
    vi.mocked(recordingsApi.getRecordingReport).mockResolvedValue(report);
    renderReport();

    const items = await screen.findAllByRole("listitem");
    await waitFor(() => expect(within(items[3]).getByText("Move unsure, possibly Counter Slash")).toBeInTheDocument());
  });

  it("says when the recording does not exist (or is someone else's)", async () => {
    vi.mocked(recordingsApi.getRecordingReport).mockRejectedValue(new ApiError(404, "Recording not found"));

    renderReport();

    expect(await screen.findByText("Recording not found.")).toBeInTheDocument();
  });

  it("deletes the recording after confirmation and returns to the list", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.mocked(recordingsApi.getRecordingReport).mockResolvedValue(makeReport());
    vi.mocked(recordingsApi.deleteRecording).mockResolvedValue(undefined);

    renderReport();
    await user.click(await screen.findByRole("button", { name: "Delete" }));

    expect(window.confirm).toHaveBeenCalledWith('Delete "genichiro.mp4" and its report? This cannot be undone.');
    expect(recordingsApi.deleteRecording).toHaveBeenCalledWith("7");
    expect(await screen.findByText("recording list")).toBeInTheDocument();
  });

  it("asks a visitor to log in", async () => {
    renderReport("en", { user: null });

    expect(await screen.findByRole("link", { name: "Log in" })).toBeInTheDocument();
    expect(recordingsApi.getRecordingReport).not.toHaveBeenCalled();
  });
});
