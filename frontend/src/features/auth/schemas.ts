import type { TFunction } from "i18next";
import { z } from "zod";

/** Mirrors the API password policy (8–128 characters, letters and digits). */
export function passwordSchema(t: TFunction) {
  return z
    .string()
    .min(8, t("auth.passwordRule"))
    .max(128, t("auth.passwordRule"))
    .regex(/[A-Za-z]/, t("auth.passwordRule"))
    .regex(/\d/, t("auth.passwordRule"));
}

export function emailSchema(t: TFunction) {
  return z.email(t("auth.invalidEmail"));
}
