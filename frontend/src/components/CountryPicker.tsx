import { useCountries } from "../api/hooks";
import { useFormat } from "../lib/format";
import { Select } from "./ui";

export function CountryPicker({
  value,
  onChange,
  id,
  label,
}: {
  value: string;
  onChange: (code: string) => void;
  id?: string;
  label?: string;
}) {
  const { data: countries = [] } = useCountries();
  const fmt = useFormat();
  const options = countries
    .map((c) => ({ code: c.code, name: fmt.country(c.code, c.name) }))
    .sort((a, b) => a.name.localeCompare(b.name, fmt.locale));
  return (
    <Select
      id={id}
      aria-label={label}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full min-w-0"
    >
      {options.map((c) => (
        <option key={c.code} value={c.code}>
          {c.name} ({c.code})
        </option>
      ))}
    </Select>
  );
}
