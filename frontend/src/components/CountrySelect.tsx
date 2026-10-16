import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "../api/client";
import { Select } from "./ui";

export function useCountries() {
  return useQuery({
    queryKey: ["countries"],
    queryFn: () => unwrap(api.GET("/api/v1/countries/")),
    staleTime: Infinity,
  });
}

export function CountrySelect({
  value,
  onChange,
  id,
}: {
  value: string;
  onChange: (code: string) => void;
  id?: string;
}) {
  const { data: countries = [] } = useCountries();
  return (
    <Select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
      {countries.map((c) => (
        <option key={c.code} value={c.code}>
          {c.name} ({c.code})
        </option>
      ))}
    </Select>
  );
}
