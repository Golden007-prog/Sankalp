import { describe, expect, test } from "vitest";
import en from "@/i18n/en.json";
import hi from "@/i18n/hi.json";
import bn from "@/i18n/bn.json";
import ta from "@/i18n/ta.json";
import kn from "@/i18n/kn.json";
import te from "@/i18n/te.json";
import mr from "@/i18n/mr.json";

const bundles = { en, hi, bn, ta, kn, te, mr } as const;
const enKeys = Object.keys(en);

describe("i18n bundle completeness", () => {
  for (const [code, bundle] of Object.entries(bundles)) {
    test(`${code} has every English key`, () => {
      const missing = enKeys.filter((k) => !(k in bundle));
      expect(missing, `${code} missing: ${missing.join(", ")}`).toHaveLength(0);
    });
  }

  for (const [code, bundle] of Object.entries(bundles)) {
    test(`${code} has no extra keys`, () => {
      const extra = Object.keys(bundle).filter((k) => !(k in en));
      expect(extra, `${code} has extras: ${extra.join(", ")}`).toHaveLength(0);
    });
  }

  test("every bundle has a non-empty lang_native", () => {
    for (const [code, b] of Object.entries(bundles)) {
      expect((b as Record<string, string>).lang_native, `${code}.lang_native missing`).toBeTruthy();
    }
  });
});
