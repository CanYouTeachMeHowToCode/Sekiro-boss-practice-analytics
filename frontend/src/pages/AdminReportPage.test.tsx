import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import RecordingReportPage from "./RecordingReportPage";
import * as adminApi from "../api/admin";
import * as bossesApi from "../api/bosses";
import * as recordingsApi from "../api/recordings";
import { genichiro, makeReport } from "../api/testRecordings";
import { testUser, withAuth } from "../auth/testAuth";
import type { AuthState } from "../auth/authContext";
import { withLanguage } from "../i18n/testLanguage";
import type { Language } from "../i18n/language";

/** The report page in the read-only admin view (owner decision, 2026-11-18). */
vi.mock("../api/bosses");
vi.mock("../api/admin", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/admin")>()),
  getAdminRecordingReport: vi.fn(),
}));
vi.mock("../api/recordings", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/recordings")>()),
  getRecordingReport: vi.fn(),
  deleteRecording: vi.fn(),
}));

const admin = { ...testUser, username: "chief", is_admin: true };

function renderAdminReport(language: Language = "en", auth: Partial<AuthState> = { user: admin }) {
  return render(
    withAuth(
      withLanguage(
        <MemoryRouter initialEntries={["/admin/recordings/7"]}>
          <Routes>
            <Route path="/admin/recordings/:recordingId" element={<RecordingReportPage admin />} />
          </Routes>
        </MemoryRouter>,
        language
      ),
      auth
    )
  );
}

describe("RecordingReportPage in the admin view", () => {
  beforeEach(() => {
    vi.mocked(bossesApi.getBossById).mockResolvedValue(genichiro);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows any user's report read-only, with whose it is and a way back to the admin list", async () => {
    vi.mocked(adminApi.getAdminRecordingReport).mockResolvedValue({ ...makeReport(), owner: "unicorn" });

    renderAdminReport();

    expect(await screen.findByRole("heading", { name: "genichiro.mp4" })).toBeInTheDocument();
    expect(adminApi.getAdminRecordingReport).toHaveBeenCalledWith("7");
    expect(recordingsApi.getRecordingReport).not.toHaveBeenCalled();
    expect(screen.getByText("unicorn")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "← All recordings" })).toHaveAttribute("href", "/admin");
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
  });

  it("shows the admin every failure's candidate scores", async () => {
    const report = { ...makeReport(), owner: "unicorn" };
    report.failures[3].candidates = [
      { move_id: "counter-slash", score: 0.1234 },
      { move_id: "hawk-shot", score: -1 },
    ];
    vi.mocked(adminApi.getAdminRecordingReport).mockResolvedValue(report);

    renderAdminReport();

    expect(await screen.findByText("Scores: Floating Passage 0.210")).toBeInTheDocument();
    expect(await screen.findByText("Scores: Counter Slash 0.123, Hawk Shot —")).toBeInTheDocument();
  });

  it("plays clips through the admin path", async () => {
    const user = userEvent.setup();
    vi.mocked(adminApi.getAdminRecordingReport).mockResolvedValue({ ...makeReport(), owner: "unicorn" });
    const { container } = renderAdminReport("zh");

    await user.click(await screen.findByRole("button", { name: "播放片段" }));

    expect(container.querySelector("video")?.getAttribute("src")).toBe("/api/admin/recordings/7/failures/1/clip");
    expect(screen.getByRole("link", { name: "← 所有录像" })).toHaveAttribute("href", "/admin");
  });

  it("is a page that does not exist for anyone but an admin", () => {
    for (const auth of [{ user: testUser }, { user: null }]) {
      const { unmount } = renderAdminReport("en", auth);
      expect(screen.getByRole("alert")).toHaveTextContent("Page not found.");
      unmount();
    }
    expect(adminApi.getAdminRecordingReport).not.toHaveBeenCalled();
    expect(recordingsApi.getRecordingReport).not.toHaveBeenCalled();
  });
});
