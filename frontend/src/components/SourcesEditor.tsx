import { useTranslation } from "react-i18next";
import type { Schemas } from "../api/client";
import { useCountries } from "../api/hooks";
import { CountryPicker } from "./CountryPicker";
import { Button, Select } from "./ui";

export type Source = Schemas["SourceRequest"];

export function SourcesEditor({
  value,
  onChange,
}: {
  value: Source[];
  onChange: (next: Source[]) => void;
}) {
  const { t } = useTranslation();
  const countries = useCountries().data ?? [];
  const update = (i: number, patch: Partial<Source>) =>
    onChange(value.map((s, j) => (j === i ? { ...s, ...patch } : s)));

  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="mb-1 text-sm font-medium">{t("sources.title")}</legend>
      {value.map((source, i) => {
        const info = countries.find((c) => c.code === source.country);
        const categories = source.categories?.length ? source.categories : ["public"];
        return (
          <div
            key={i}
            className="flex flex-wrap items-center gap-2 rounded-lg border border-line p-2"
          >
            <div className="min-w-48 flex-1">
              <CountryPicker
                label={t("sources.country")}
                value={source.country}
                onChange={(country) => update(i, { country, subdiv: "", categories: [] })}
              />
            </div>
            {info && info.subdivisions.length > 0 && (
              <Select
                aria-label={t("sources.subdivision")}
                value={source.subdiv ?? ""}
                onChange={(e) => update(i, { subdiv: e.target.value })}
              >
                <option value="">{t("sources.wholeCountry")}</option>
                {info.subdivisions.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </Select>
            )}
            {info && info.categories.length > 1 && (
              <div
                className="flex flex-wrap gap-2 text-sm"
                role="group"
                aria-label={t("sources.categories")}
              >
                {info.categories.map((c) => (
                  <label key={c} className="flex items-center gap-1">
                    <input
                      type="checkbox"
                      className="accent-accent"
                      checked={categories.includes(c)}
                      onChange={(e) =>
                        update(i, {
                          categories: e.target.checked
                            ? [...categories, c]
                            : categories.filter((x) => x !== c),
                        })
                      }
                    />
                    {c}
                  </label>
                ))}
              </div>
            )}
            {value.length > 1 && (
              <Button variant="danger" onClick={() => onChange(value.filter((_, j) => j !== i))}>
                {t("common.remove")}
              </Button>
            )}
          </div>
        );
      })}
      <div>
        <Button variant="ghost" onClick={() => onChange([...value, { country: "SA" }])}>
          {t("sources.add")}
        </Button>
      </div>
    </fieldset>
  );
}
