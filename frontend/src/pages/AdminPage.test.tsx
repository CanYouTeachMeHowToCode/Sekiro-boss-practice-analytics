import { act, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import AdminPage from "./AdminPage";
import * as adminApi from "../api/admin";
import { makeRecording } from "../api/testRecordings";
import { testUser, withAuth } from "../auth/testAuth";
import type { AuthState } from "../auth/authContext";
import { withLanguage } from "../i18n/testLanguage";
import type { Language } from "../i18n/language";
import type { AdminRecording } from "../types";
import { LIST_POLL_MS } from "../utils/recordings";

vi.mock("../api/admin", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/admin")>()),
  listAdminRecordings: vi.fn(),
}));

const admin = { ...testUser, username: "chief", is_admin: true };

function adminRecording(overrides: Partial<AdminRecording> = {}): AdminRecording {
  return { ...makeRecording(), owner: "unicorn", error: null, fps: 59.94, ...overrides };
}

function renderAdmin(language: Language = "en", auth: Partial<AuthState> = { user: admin }) {
  return render(
    withAuth(
      withLanguage(
        <MemoryRouter>
          <AdminPage />
        </MemoryRouter>,
        language
      ),
      auth
    )
  );
}

describe("AdminPage", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("lists every user's recordings with their owner, status and a link to each report", async () => {
    vi.mocked(adminApi.listAdminRecordings).mockResolvedValue([
      adminRecording({ id: "9", filename: "queued.mp4", status: "queued", owner: "wolf" }),
      adminRecording({ id: "8", filename: "rejected.mp4", status: "rejected", reject_code: "not_sekiro" }),
      adminRecording({ id: "7", filename: "broken.mp4", status: "failed", error: "ffmpeg exited with 1" }),
      adminRecording({ id: "6", filename: "done.mp4" }),
    ]);

    renderAdmin();

    expect(await screen.findByRole("heading", { name: "All Recordings" })).toBeInTheDocument();
    const rows = within(screen.getByRole("table")).getAllByRole("row").slice(1);
    expect(rows.map((row) => within(row).getByRole("link").getAttribute("href"))).toEqual([
      "/admin/recordings/9",
      "/admin/recordings/8",
      "/admin/recordings/7",
      "/admin/recordings/6",
    ]);
    expect(within(rows[0]).getByText("wolf")).toBeInTheDocument();
    expect(within(rows[0]).getByText("Waiting to be analysed")).toBeInTheDocument();
    expect(within(rows[1]).getByText(/not look like a Sekiro recording/)).toBeInTheDocument();
    expect(within(rows[2]).getByText("ffmpeg exited with 1")).toBeInTheDocument();
    expect(within(rows[3]).getByText("2560×1440 · 5:07 · 60 fps")).toBeInTheDocument();
    expect(within(rows[3]).getByText("Report ready")).toBeInTheDocument();
  });

  it("checks for new uploads and progress every few seconds, in Chinese too", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.mocked(adminApi.listAdminRecordings)
      .mockResolvedValueOnce([adminRecording({ status: "processing", progress: 0.4 })])
      .mockResolvedValueOnce([adminRecording({ status: "done" })]);

    renderAdmin("zh");

    expect(await screen.findByRole("heading", { name: "所有录像" })).toBeInTheDocument();
    expect(await screen.findByText("分析中：40%")).toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(LIST_POLL_MS));
    expect(await screen.findByText("报告已生成")).toBeInTheDocument();
  });

  it("is a page that does not exist for anyone but an admin", async () => {
    for (const auth of [{ user: testUser }, { user: null }]) {
      const { unmount } = renderAdmin("en", auth);
      expect(screen.getByRole("alert")).toHaveTextContent("Page not found.");
      expect(screen.queryByRole("table")).not.toBeInTheDocument();
      unmount();
    }
    expect(adminApi.listAdminRecordings).not.toHaveBeenCalled();
  });

  it("says when the list cannot be loaded", async () => {
    vi.mocked(adminApi.listAdminRecordings).mockRejectedValue(new Error("offline"));

    renderAdmin();

    expect(await screen.findByRole("alert")).toHaveTextContent("Failed to load the recordings.");
  });
});
