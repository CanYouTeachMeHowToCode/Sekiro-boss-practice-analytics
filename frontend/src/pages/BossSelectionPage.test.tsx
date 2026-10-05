import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import BossSelectionPage from "./BossSelectionPage";
import { withLanguage } from "../i18n/testLanguage";
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
      { id: "genichiro-ashina", name: "Genichiro Ashina", name_zh: "苇名弦一郎", location: "Ashina Castle", location_zh: "苇名城" },
    ]);

    renderPage();

    expect(await screen.findByText("Genichiro Ashina")).toBeInTheDocument();
    expect(screen.queryByText("苇名弦一郎")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view boss/i })).toHaveAttribute("href", "/bosses/genichiro-ashina");
    expect(screen.getByRole("link", { name: /home/i })).toHaveAttribute("href", "/");
  });

  it("shows an error message when the boss list fails to load", async () => {
    vi.mocked(bossesApi.getBosses).mockRejectedValue(new Error("network error"));

    renderPage();

    expect(await screen.findByRole("alert")).toHaveTextContent(/failed to load bosses/i);
  });

  it("shows Chinese boss names and locations in Chinese mode", async () => {
    vi.mocked(bossesApi.getBosses).mockResolvedValue([
      { id: "genichiro-ashina", name: "Genichiro Ashina", name_zh: "苇名弦一郎", location: "Ashina Castle", location_zh: "苇名城" },
    ]);

    render(withLanguage(<MemoryRouter><BossSelectionPage /></MemoryRouter>, "zh"));

    expect(await screen.findByText("苇名弦一郎")).toBeInTheDocument();
    expect(screen.getByText("苇名城")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "查看 Boss" })).toHaveAttribute("href", "/bosses/genichiro-ashina");
    expect(screen.queryByText("Genichiro Ashina")).not.toBeInTheDocument();
  });
});
