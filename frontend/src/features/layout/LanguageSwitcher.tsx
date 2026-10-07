import { Languages } from "lucide-react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";
import { LANGUAGES, type Language, currentLanguage, setLanguage } from "@/i18n";

/** Interface language for this browser (signed-in users also save it in their profile). */
export function LanguageSwitcher({
  onChange,
  className,
}: {
  onChange?: (language: Language) => void;
  className?: string;
}) {
  const { t } = useTranslation();
  return (
    <label className={cn("inline-flex items-center gap-2 text-sm", className)}>
      <Languages className="size-4" aria-hidden="true" />
      <span className="sr-only">{t("common.language")}</span>
      <select
        className="rounded-md border border-current/20 bg-transparent px-2 py-1"
        value={currentLanguage()}
        onChange={(event) => {
          const language = event.target.value as Language;
          void setLanguage(language);
          onChange?.(language);
        }}
      >
        {LANGUAGES.map((language) => (
          <option key={language} value={language} className="text-ink">
            {t(`languages.${language}`)}
          </option>
        ))}
      </select>
    </label>
  );
}
