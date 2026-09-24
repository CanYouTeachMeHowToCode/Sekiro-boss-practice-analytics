import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as authApi from "../api/auth";
import { withAuth } from "../auth/testAuth";
import type { AuthState } from "../auth/authContext";
import NavBar from "../components/NavBar";
import type { User } from "../types";
import LanguageProvider from "./LanguageProvider";
import { useLanguage } from "./language";

vi.mock("../api/auth");

function Probe() {
  const { language, t } = useLanguage();
  return (
    <p>
      {language}: {t("nav.bosses")}
    </p>
  );
}

function renderWith(auth: Partial<AuthState>) {
  return render(
    withAuth(
      <MemoryRouter>
        <LanguageProvider>
          <NavBar />
          <Probe />
        </LanguageProvider>
      </MemoryRouter>,
      auth
    )
  );
}

function setBrowserLanguage(language: string) {
  vi.spyOn(window.navigator, "language", "get").mockReturnValue(language);
}

const user = (preferred_language: User["preferred_language"]): User => ({ id: "1", username: "wolf", preferred_language });

describe("LanguageProvider", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.mocked(authApi.updatePreferredLanguage).mockResolvedValue(user("zh"));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("follows the browser language on a first visit", () => {
    setBrowserLanguage("zh-CN");

    renderWith({ user: null });

    expect(screen.getByText("zh: Boss 列表")).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("zh-Hans");
  });

  it("keeps a visitor's choice in the browser without calling the API", async () => {
    setBrowserLanguage("en-US");
    renderWith({ user: null });

    await userEvent.click(screen.getByRole("button", { name: "Switch to Chinese" }));

    expect(screen.getByText("zh: Boss 列表")).toBeInTheDocument();
    expect(window.localStorage.getItem("language")).toBe("zh");
    expect(authApi.updatePreferredLanguage).not.toHaveBeenCalled();
  });

  it("uses a stored choice over the browser language", () => {
    setBrowserLanguage("en-US");
    window.localStorage.setItem("language", "zh");

    renderWith({ user: null });

    expect(screen.getByText("zh: Boss 列表")).toBeInTheDocument();
  });

  it("adopts the language saved in the account when the user is logged in", async () => {
    setBrowserLanguage("en-US");

    renderWith({ user: user("zh") });

    expect(await screen.findByText("zh: Boss 列表")).toBeInTheDocument();
  });

  it("saves a logged-in user's choice to their account", async () => {
    setBrowserLanguage("en-US");
    renderWith({ user: user(null) });

    await userEvent.click(screen.getByRole("button", { name: "Switch to Chinese" }));

    expect(screen.getByText("zh: Boss 列表")).toBeInTheDocument();
    await waitFor(() => expect(authApi.updatePreferredLanguage).toHaveBeenCalledWith("zh"));

    await userEvent.click(screen.getByRole("button", { name: "切换到英文" }));
    expect(screen.getByText("en: Bosses")).toBeInTheDocument();
    expect(authApi.updatePreferredLanguage).toHaveBeenLastCalledWith("en");
  });
});
