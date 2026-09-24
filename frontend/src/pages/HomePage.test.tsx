import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import * as bossesApi from "../api/bosses";
import * as sekiroApi from "../api/sekiro";
import { withAuth } from "../auth/testAuth";
import type { AuthState } from "../auth/authContext";
import NavBar from "../components/NavBar";
import HomePage from "./HomePage";

vi.mock("../api/bosses");
vi.mock("../api/sekiro");

function renderHome(auth: Partial<AuthState>) {
  return render(
    withAuth(
      <MemoryRouter>
        <NavBar />
        <HomePage />
      </MemoryRouter>,
      auth
    )
  );
}

describe("HomePage and NavBar", () => {
  it("welcomes visitors with the boss list and login links", async () => {
    vi.mocked(bossesApi.getBosses).mockResolvedValue([
      { id: "genichiro-ashina", name: "Genichiro Ashina", name_zh: "苇名弦一郎", location: "Ashina Castle" },
    ]);

    renderHome({ user: null });

    expect(await screen.findByText("Genichiro Ashina")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Create an Account" })).toHaveAttribute("href", "/register");
    // One in the nav bar, one in the welcome text.
    for (const link of screen.getAllByRole("link", { name: "Log In" })) {
      expect(link).toHaveAttribute("href", "/login");
    }
    expect(sekiroApi.getSekiroAnalytics).not.toHaveBeenCalled();
  });

  it("shows a logged-in player their dashboard and a logout button", async () => {
    vi.mocked(sekiroApi.getSekiroAnalytics).mockReturnValue(new Promise(() => undefined));

    renderHome({});

    expect(screen.getByText("wolf")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Log Out" })).toBeInTheDocument();
    expect(sekiroApi.getSekiroAnalytics).toHaveBeenCalled();
    expect(bossesApi.getBosses).not.toHaveBeenCalled();
  });
});
