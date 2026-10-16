import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "./client";

export type Target = { country: string } | { calendar: string };

export function useCountries() {
  return useQuery({
    queryKey: ["countries"],
    queryFn: () => unwrap(api.GET("/api/v1/countries/")),
    staleTime: Infinity,
  });
}

export function useDayRange(target: Target, start: string, end: string, language?: string) {
  const query = { ...target, start, end, ...("country" in target ? { language } : {}) };
  return useQuery({
    queryKey: ["range", query],
    queryFn: () => unwrap(api.GET("/api/v1/business-days/range/", { params: { query } })),
    placeholderData: (previous) => previous,
  });
}

export function useHolidays(target: Target, year: number, language?: string) {
  return useQuery({
    queryKey: ["holidays", target, year, language],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/holidays/", {
          params: { query: { ...target, year, ...("country" in target ? { language } : {}) } },
        }),
      ),
    placeholderData: (previous) => previous,
  });
}
