import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import ar from "./locales/ar.json";
import en from "./locales/en.json";
import fr from "./locales/fr.json";

export const LANGUAGES = ["en", "fr", "ar"] as const;
export type Language = (typeof LANGUAGES)[number];

/** Locales used for dates and numbers. ar-MA keeps Latin digits, as used in Morocco. */
export const FORMAT_LOCALES: Record<Language, string> = {
  en: "en-GB",
  fr: "fr-FR",
  ar: "ar-MA",
};

const STORAGE_KEY = "car-checker.language";

export function isLanguage(value: unknown): value is Language {
  return typeof value === "string" && (LANGUAGES as readonly string[]).includes(value);
}

function initialLanguage(): Language {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (isLanguage(stored)) return stored;
  } catch {
    // storage unavailable
  }
  const browser = navigator.language.slice(0, 2);
  return isLanguage(browser) ? browser : "en";
}

function applyDocumentLanguage(language: Language): void {
  document.documentElement.lang = language;
  document.documentElement.dir = language === "ar" ? "rtl" : "ltr";
}

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, fr: { translation: fr }, ar: { translation: ar } },
  lng: initialLanguage(),
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});
applyDocumentLanguage(i18n.language as Language);

/** Switch the interface language (also sets <html lang dir> and remembers the choice). */
export async function setLanguage(language: Language): Promise<void> {
  try {
    localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // storage unavailable
  }
  applyDocumentLanguage(language);
  await i18n.changeLanguage(language);
}

export function currentLanguage(): Language {
  return isLanguage(i18n.language) ? i18n.language : "en";
}

export { i18n };
