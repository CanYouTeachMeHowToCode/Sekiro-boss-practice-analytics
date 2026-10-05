import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { updatePreferredLanguage } from "../api/auth";
import { useAuth } from "../auth/authContext";
import { LanguageContext, makeTranslate } from "./language";
import type { Language } from "./language";

const STORAGE_KEY = "language";

function isLanguage(value: unknown): value is Language {
  return value === "en" || value === "zh";
}

function readStoredLanguage(): Language | null {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return isLanguage(stored) ? stored : null;
  } catch {
    return null;
  }
}

function storeLanguage(language: Language): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // Private mode or blocked storage: the choice just won't survive a reload.
  }
}

function browserLanguage(): Language {
  return typeof navigator !== "undefined" && navigator.language.toLowerCase().startsWith("zh") ? "zh" : "en";
}

/**
 * The interface language. Logged-in users keep it in their account so it follows
 * them across devices; visitors keep it in this browser. The first visit follows
 * the browser's language.
 */
export default function LanguageProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [language, setLanguageState] = useState<Language>(() => readStoredLanguage() ?? browserLanguage());

  // Logging in adopts the language saved in the account, if the user has picked one.
  const accountLanguage = user?.preferred_language ?? null;
  useEffect(() => {
    if (accountLanguage) {
      setLanguageState(accountLanguage);
      storeLanguage(accountLanguage);
    }
  }, [accountLanguage]);

  useEffect(() => {
    document.documentElement.lang = language === "zh" ? "zh-Hans" : "en";
  }, [language]);

  const loggedIn = user !== null;
  const setLanguage = useCallback(
    (next: Language) => {
      setLanguageState(next);
      storeLanguage(next);
      if (loggedIn) {
        // Best effort: the switch already happened locally.
        updatePreferredLanguage(next).catch(() => undefined);
      }
    },
    [loggedIn]
  );

  const value = useMemo(() => ({ language, setLanguage, t: makeTranslate(language) }), [language, setLanguage]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}
