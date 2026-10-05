import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import * as authApi from "../api/auth";
import { UNAUTHORIZED_EVENT } from "../api/client";
import AuthProvider from "./AuthProvider";
import { useAuth } from "./authContext";

vi.mock("../api/auth");

function Probe() {
  const { status, user, login, logout } = useAuth();
  return (
    <div>
      <p>status: {status}</p>
      <p>user: {user?.username ?? "none"}</p>
      <button onClick={() => login({ username: "wolf", password: "kusabimaru" })}>login</button>
      <button onClick={() => logout()}>logout</button>
    </div>
  );
}

function renderProbe() {
  return render(
    <AuthProvider>
      <Probe />
    </AuthProvider>
  );
}

describe("AuthProvider", () => {
  it("restores the logged-in user from the session cookie", async () => {
    vi.mocked(authApi.getCurrentUser).mockResolvedValue({ id: "1", username: "wolf", preferred_language: null });

    renderProbe();

    expect(screen.getByText("status: loading")).toBeInTheDocument();
    expect(await screen.findByText("user: wolf")).toBeInTheDocument();
    expect(screen.getByText("status: ready")).toBeInTheDocument();
  });

  it("logs in and out", async () => {
    vi.mocked(authApi.getCurrentUser).mockResolvedValue(null);
    vi.mocked(authApi.login).mockResolvedValue({ id: "1", username: "wolf", preferred_language: null });
    vi.mocked(authApi.logout).mockResolvedValue(undefined);
    renderProbe();
    await screen.findByText("status: ready");

    await userEvent.click(screen.getByRole("button", { name: "login" }));
    expect(await screen.findByText("user: wolf")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "logout" }));
    expect(await screen.findByText("user: none")).toBeInTheDocument();
  });

  it("forgets the user when any request comes back 401", async () => {
    vi.mocked(authApi.getCurrentUser).mockResolvedValue({ id: "1", username: "wolf", preferred_language: null });
    renderProbe();
    await screen.findByText("user: wolf");

    act(() => {
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    });

    expect(screen.getByText("user: none")).toBeInTheDocument();
  });
});
