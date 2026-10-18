import createClient from "openapi-fetch";
import type { components, paths } from "./schema";

export type Schemas = components["schemas"];

export interface Options {
  /** `hops_<prefix>_<secret>` from your organization settings; without one, 60 requests a minute per IP. */
  apiKey?: string;
  /** Defaults to the hosted API. */
  baseUrl?: string;
}

/** Typed client for the HolidayOps public API, generated from its OpenAPI schema. */
export function holidayops({ apiKey, baseUrl = "https://holidayops.ahmershah.dev" }: Options = {}) {
  const client = createClient<paths>({
    baseUrl,
    headers: apiKey ? { Authorization: `Bearer ${apiKey}` } : {},
  });
  return {
    raw: client,
    countries: () => client.GET("/api/v1/countries/"),
    holidays: (query: paths["/api/v1/holidays/"]["get"]["parameters"]["query"]) =>
      client.GET("/api/v1/holidays/", { params: { query } }),
    check: (query: paths["/api/v1/business-days/check/"]["get"]["parameters"]["query"]) =>
      client.GET("/api/v1/business-days/check/", { params: { query } }),
    add: (query: paths["/api/v1/business-days/add/"]["get"]["parameters"]["query"]) =>
      client.GET("/api/v1/business-days/add/", { params: { query } }),
    between: (query: paths["/api/v1/business-days/between/"]["get"]["parameters"]["query"]) =>
      client.GET("/api/v1/business-days/between/", { params: { query } }),
  };
}
