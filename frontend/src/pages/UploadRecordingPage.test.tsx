import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import UploadRecordingPage from "./UploadRecordingPage";
import * as recordingsApi from "../api/recordings";
import { makeRecording } from "../api/testRecordings";
import { withAuth } from "../auth/testAuth";
import type { AuthState } from "../auth/authContext";
import { withLanguage } from "../i18n/testLanguage";
import type { Language } from "../i18n/language";

vi.mock("../api/recordings", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/recordings")>()),
  uploadRecording: vi.fn(),
}));

function renderUpload(language: Language = "en", auth: Partial<AuthState> = {}) {
  return render(
    withAuth(
      withLanguage(
        <MemoryRouter initialEntries={["/recordings/upload"]}>
          <Routes>
            <Route path="/recordings/upload" element={<UploadRecordingPage />} />
            <Route path="/recordings/:recordingId" element={<p>report page</p>} />
          </Routes>
        </MemoryRouter>,
        language
      ),
      auth
    )
  );
}

function video(name = "fight.mp4") {
  return new File([new Uint8Array(16)], name, { type: "video/mp4" });
}

describe("UploadRecordingPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("states what can be analysed and recommends at least 1080p and 60 fps", () => {
    renderUpload();

    expect(screen.getByText(/in vanilla Sekiro/)).toBeInTheDocument();
    expect(screen.getByText(/a constant 30 or 60 frames per second/)).toBeInTheDocument();
    expect(screen.getByText(/30 fps videos are analysed too, but .* for reference only/)).toBeInTheDocument();
    expect(
      screen.getByText(
        "Record at 1080p or higher if you can. 720p videos are analysed too, but more failures will show the move as unsure."
      )
    ).toBeInTheDocument();
  });

  it("says the same in Chinese", () => {
    renderUpload("zh");

    expect(screen.getByText(/原版《只狼》/)).toBeInTheDocument();
    expect(screen.getByText("建议用 60 帧录制。30 帧也能分析，但 30 帧的识别还在验证，结果仅供参考。")).toBeInTheDocument();
    expect(
      screen.getByText('建议用 1080p 或更高分辨率录制。720p 也能分析，但更多失败会显示"招式不确定"。')
    ).toBeInTheDocument();
  });

  it("shows the upload's progress and then opens the recording's page", async () => {
    const user = userEvent.setup();
    let report: (fraction: number) => void = () => undefined;
    let finish: (value: ReturnType<typeof makeRecording>) => void = () => undefined;
    vi.mocked(recordingsApi.uploadRecording).mockImplementation((_file, onProgress) => {
      report = onProgress;
      return new Promise((resolve) => {
        finish = resolve;
      });
    });

    renderUpload();
    await user.upload(screen.getByLabelText("Video file"), video());
    await user.click(screen.getByRole("button", { name: "Upload" }));

    act(() => report(0.37));
    expect(await screen.findByText("Uploading: 37%")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Upload" })).toBeDisabled();
    await act(async () => finish(makeRecording({ id: "9", status: "uploaded" })));
    expect(await screen.findByText("report page")).toBeInTheDocument();
  });

  it("refuses a file the backend would refuse without sending it", async () => {
    const user = userEvent.setup({ applyAccept: false });

    renderUpload();
    await user.upload(screen.getByLabelText("Video file"), video("notes.txt"));

    expect(screen.getByRole("alert")).toHaveTextContent("Only MP4, MKV and MOV files can be uploaded.");
    expect(screen.getByRole("button", { name: "Upload" })).toBeDisabled();
    expect(recordingsApi.uploadRecording).not.toHaveBeenCalled();
  });

  it("shows why an upload failed and lets it be sent again", async () => {
    const user = userEvent.setup();
    vi.mocked(recordingsApi.uploadRecording)
      .mockRejectedValueOnce(new recordingsApi.UploadError("network"))
      .mockResolvedValueOnce(makeRecording({ id: "9" }));

    renderUpload();
    await user.upload(screen.getByLabelText("Video file"), video());
    await user.click(screen.getByRole("button", { name: "Upload" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("The connection was lost during the upload.");
    await user.click(screen.getByRole("button", { name: "Upload" }));
    expect(await screen.findByText("report page")).toBeInTheDocument();
  });

  it("asks a visitor to log in instead of showing the form", () => {
    renderUpload("en", { user: null });

    expect(screen.getByRole("link", { name: "Log in" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Video file")).not.toBeInTheDocument();
  });
});
