import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Outlet } from "react-router";

import { Odometer } from "@/components/ui";
import { FORMAT_LOCALES, currentLanguage } from "@/i18n";
import { formatNumber } from "@/lib/format";

import { LanguageSwitcher } from "../layout/LanguageSwitcher";

const SHOWCASE_KM = 128_450;

/** Sign-in pages: the odometer rolls once to its reading as the page opens. */
export function AuthLayout() {
  const { t } = useTranslation();
  const [reading, setReading] = useState(0);
  useEffect(() => {
    const timer = window.setTimeout(() => setReading(SHOWCASE_KM), 150);
    return () => window.clearTimeout(timer);
  }, []);
  const locale = FORMAT_LOCALES[currentLanguage()];

  return (
    <div className="grid min-h-dvh lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      <aside className="flex flex-col justify-between gap-10 bg-ink px-6 py-8 text-white sm:px-10 lg:py-12">
        <p className="font-display text-2xl font-bold">{t("app.name")}</p>
        <div className="flex flex-col gap-6">
          <Odometer
            className="self-start"
            value={reading}
            unit="km"
            label={`${formatNumber(locale, SHOWCASE_KM)} km`}
          />
          <p className="max-w-sm font-display text-3xl leading-tight font-semibold sm:text-4xl">
            {t("auth.hero")}
          </p>
        </div>
        <p className="hidden max-w-sm text-white/70 lg:block">{t("auth.heroBody")}</p>
      </aside>
      <main className="flex flex-col px-6 py-8 sm:px-10">
        <div className="flex justify-end">
          <LanguageSwitcher />
        </div>
        <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center py-10">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
