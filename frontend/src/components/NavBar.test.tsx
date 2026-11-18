import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import NavBar from "./NavBar";
import { testUser, withAuth } from "../auth/testAuth";
import type { AuthState } from "../auth/authContext";
import { withLanguage } from "../i18n/testLanguage";
import type { Language } from "../i18n/language";

function renderNav(auth: Partial<AuthState>, language: Language = "en") {
  return render(
    withAuth(
      withLanguage(
        <MemoryRouter>
          <NavBar />
        </MemoryRouter>,
        language
      ),
      auth
    )
  );
}

describe("NavBar", () => {
  it("shows the admin link to admins only", () => {
    const { unmount } = renderNav({ user: { ...testUser, is_admin: true } });
    expect(screen.getByRole("link", { name: "Admin" })).toHaveAttribute("href", "/admin");
    unmount();

    renderNav({ user: { ...testUser, is_admin: true } }, "zh");
    expect(screen.getByRole("link", { name: "管理" })).toHaveAttribute("href", "/admin");
  });

  it("has no admin link for other users or visitors", () => {
    for (const user of [testUser, null]) {
      const { unmount } = renderNav({ user });
      expect(screen.queryByRole("link", { name: "Admin" })).not.toBeInTheDocument();
      unmount();
    }
  });
});
