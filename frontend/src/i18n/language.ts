import { createContext, useContext } from "react";
import { messages } from "./messages";
import type { Language, MessageKey } from "./messages";

export type { Language, MessageKey };

export type Translate = (key: MessageKey, params?: Record<string, string | number>) => string;

export function makeTranslate(language: Language): Translate {
  return (key, params) => {
    const template = messages[language][key];
    if (!params) return template;
    return template.replace(/\{(\w+)\}/g, (match, name: string) => (name in params ? String(params[name]) : match));
  };
}

const CHINESE_NUMERALS = ["", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"];

/** "Phase 2" / "第二阶段", matching the phase names in the boss data. */
export function formatPhase(phase: number | string, language: Language): string {
  const n = Number(phase);
  if (language === "zh") return `第${CHINESE_NUMERALS[n] ?? n}阶段`;
  return `Phase ${n}`;
}

/** Locale for dates and numbers; undefined keeps the browser default for English. */
export function localeFor(language: Language): string | undefined {
  return language === "zh" ? "zh-CN" : undefined;
}

export interface LanguageState {
  language: Language;
  setLanguage: (language: Language) => void;
  t: Translate;
}

// English without a provider, so components render the same as before in isolation.
export const LanguageContext = createContext<LanguageState>({
  language: "en",
  setLanguage: () => undefined,
  t: makeTranslate("en"),
});

export function useLanguage(): LanguageState {
  return useContext(LanguageContext);
}
