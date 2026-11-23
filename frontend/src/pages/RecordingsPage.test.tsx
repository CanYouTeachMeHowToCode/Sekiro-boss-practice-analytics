import { act, cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import RecordingsPage from "./RecordingsPage";
import * as recordingsApi from "../api/recordings";
import { makeRecording } from "../api/testRecordings";
import { withAuth } from "../auth/testAuth";
import type { AuthState } from "../auth/authContext";
import { withLanguage } from "../i18n/testLanguage";
import type { Language } from "../i18n/language";
import { LIST_POLL_MS } from "../utils/recordings";

vi.mock("../api/recordings", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/recordings")>()),
  listRecordings: vi.fn(),
  deleteRecording: vi.fn(),
}));

function renderList(language: Language = "en", auth: Partial<AuthState> = {}) {
  return render(
    withAuth(
      withLanguage(
        <MemoryRouter>
          <RecordingsPage />
        </MemoryRouter>,
        language
      ),
      auth
    )
  );
}

describe("RecordingsPage", () => {
  afterEach(() => {
    vi.useRealTimers();
    // unmount first: a pending effect that calls a mocked API must run before the mocks are restored
    cleanup();
    vi.restoreAllMocks();
  });

  it("lists the recordings with their status and links to each report", async () => {
    vi.mocked(recordingsApi.listRecordings).mockResolvedValue([
      makeRecording({ id: "8", filename: "new.mp4", status: "rejected", reject_code: "too_long" }),
      makeRecording({ id: "7", filename: "genichiro.mp4", width: 1280, height: 720, low_resolution: true }),
    ]);

    renderList();

    const items = await screen.findAllByRole("listitem");
    expect(items.map((item) => within(item).getByRole("link").getAttribute("href"))).toEqual([
      "/recordings/8",
      "/recordings/7",
    ]);
    expect(within(items[0]).getByText("Not analysed")).toBeInTheDocument();
    expect(within(items[1]).getByText("Report ready")).toBeInTheDocument();
    expect(within(items[1]).getByText(/5:07 · 720p$/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "+ Upload a Recording" })).toHaveAttribute("href", "/recordings/upload");
  });

  it("checks again while a recording is being analysed", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.mocked(recordingsApi.listRecordings)
      .mockResolvedValueOnce([makeRecording({ status: "processing", progress: 0.1 })])
      .mockResolvedValueOnce([makeRecording({ status: "done" })]);

    renderList("zh");

    expect(await screen.findByText("分析中：10%")).toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(LIST_POLL_MS));
    expect(await screen.findByText("报告已生成")).toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(LIST_POLL_MS * 2));
    expect(recordingsApi.listRecordings).toHaveBeenCalledTimes(2);
  });

  it("deletes a recording only after confirmation", async () => {
    const user = userEvent.setup();
    const confirm = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
    vi.mocked(recordingsApi.listRecordings).mockResolvedValue([makeRecording()]);
    vi.mocked(recordingsApi.deleteRecording).mockResolvedValue(undefined);

    renderList();
    const button = await screen.findByRole("button", { name: "Delete" });
    await user.click(button);
    expect(recordingsApi.deleteRecording).not.toHaveBeenCalled();
    await user.click(button);

    expect(confirm).toHaveBeenCalledTimes(2);
    expect(recordingsApi.deleteRecording).toHaveBeenCalledWith("7");
    expect(await screen.findByText("No recordings yet.")).toBeInTheDocument();
  });

  it("asks a visitor to log in", async () => {
    renderList("en", { user: null });

    expect(screen.getByRole("link", { name: "Log in" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "+ Upload a Recording" })).not.toBeInTheDocument();
    expect(recordingsApi.listRecordings).not.toHaveBeenCalled();
  });

  it("says when the list cannot be loaded", async () => {
    vi.mocked(recordingsApi.listRecordings).mockRejectedValue(new Error("offline"));

    renderList();

    expect(await screen.findByRole("alert")).toHaveTextContent("Failed to load your recordings.");
  });
});
