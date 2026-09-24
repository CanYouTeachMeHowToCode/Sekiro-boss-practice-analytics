import type { ReactElement } from "react";
import { vi } from "vitest";
import { LanguageContext, makeTranslate } from "./language";
import type { Language } from "./language";

/** Renders `ui` in a fixed interface language for component tests. */
export function withLanguage(ui: ReactElement, language: Language, setLanguage = vi.fn()): ReactElement {
  return (
    <LanguageContext.Provider value={{ language, setLanguage, t: makeTranslate(language) }}>{ui}</LanguageContext.Provider>
  );
}
