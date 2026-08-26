import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import BossSelectionPage from "./BossSelectionPage";
import * as bossesApi from "../api/bosses";

vi.mock("../api/bosses");

function renderPage() {
  return render(
    <MemoryRouter>
      <BossSelectionPage />
    </MemoryRouter>
  );
}

describe("BossSelectionPage", () => {
  it("renders each boss returned by the API as a link to its dashboard", async () => {
    vi.mocked(bossesApi.getBosses).mockResolvedValue([
      { id: "genichiro-ashina", name: "Genichiro Ashina", location: "Ashina Castle" },
    ]);

    renderPage();

    expect(await screen.findByText("Genichiro Ashina")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view boss/i })).toHaveAttribute("href", "/bosses/genichiro-ashina");
  });

  it("shows an error message when the boss list fails to load", async () => {
    vi.mocked(bossesApi.getBosses).mockRejectedValue(new Error("network error"));

    renderPage();

    expect(await screen.findByRole("alert")).toHaveTextContent(/failed to load bosses/i);
  });
});
