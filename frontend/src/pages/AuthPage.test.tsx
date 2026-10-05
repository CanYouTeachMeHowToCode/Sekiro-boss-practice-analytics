import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import { withAuth } from "../auth/testAuth";
import type { AuthState } from "../auth/authContext";
import AuthPage from "./AuthPage";

function renderAuthPage(mode: "login" | "register", auth: Partial<AuthState>, from?: string) {
  return render(
    withAuth(
      <MemoryRouter initialEntries={[{ pathname: `/${mode}`, state: from ? { from } : null }]}>
        <Routes>
          <Route path="/login" element={<AuthPage mode="login" />} />
          <Route path="/register" element={<AuthPage mode="register" />} />
          <Route path="/" element={<p>home page</p>} />
          <Route path="/bosses/:bossId" element={<p>boss page</p>} />
        </Routes>
      </MemoryRouter>,
      auth
    )
  );
}

async function fillAndSubmit(button: string) {
  await userEvent.type(screen.getByLabelText("Username"), "wolf");
  await userEvent.type(screen.getByLabelText("Password"), "kusabimaru");
  await userEvent.click(screen.getByRole("button", { name: button }));
}

describe("AuthPage", () => {
  it("logs in and returns to the page the user came from", async () => {
    const login = vi.fn().mockResolvedValue(undefined);
    renderAuthPage("login", { user: null, login }, "/bosses/genichiro-ashina");

    await fillAndSubmit("Log In");

    expect(login).toHaveBeenCalledWith({ username: "wolf", password: "kusabimaru" });
    expect(await screen.findByText("boss page")).toBeInTheDocument();
  });

  it("shows a clear message for wrong credentials", async () => {
    const login = vi.fn().mockRejectedValue(new ApiError(401, "Incorrect username or password"));
    renderAuthPage("login", { user: null, login });

    await fillAndSubmit("Log In");

    expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect username or password.");
    expect(screen.getByRole("button", { name: "Log In" })).toBeEnabled();
  });

  it("registers and goes to the home page", async () => {
    const register = vi.fn().mockResolvedValue(undefined);
    renderAuthPage("register", { user: null, register });

    await fillAndSubmit("Register");

    expect(register).toHaveBeenCalledWith({ username: "wolf", password: "kusabimaru" });
    expect(await screen.findByText("home page")).toBeInTheDocument();
  });

  it("explains a taken username", async () => {
    const register = vi.fn().mockRejectedValue(new ApiError(409, "Username 'wolf' is already taken"));
    renderAuthPage("register", { user: null, register });

    await fillAndSubmit("Register");

    expect(await screen.findByRole("alert")).toHaveTextContent("That username is already taken.");
  });

  it("sends an already logged-in user straight on", () => {
    renderAuthPage("login", {});

    expect(screen.getByText("home page")).toBeInTheDocument();
  });

  it("shows and hides the typed password with the eye button", async () => {
    renderAuthPage("login", { user: null });
    const password = screen.getByLabelText("Password");
    await userEvent.type(password, "kusabimaru");

    expect(password).toHaveAttribute("type", "password");

    await userEvent.click(screen.getByRole("button", { name: "Show password" }));
    expect(password).toHaveAttribute("type", "text");
    expect(password).toHaveValue("kusabimaru");

    await userEvent.click(screen.getByRole("button", { name: "Hide password" }));
    expect(password).toHaveAttribute("type", "password");
  });
});
