import createClient, { type Middleware } from "openapi-fetch";
import type { components, paths } from "./schema";

export type Schemas = components["schemas"];

const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export function readCookie(name: string, cookie = document.cookie): string | null {
  for (const part of cookie.split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === name) return decodeURIComponent(rest.join("="));
  }
  return null;
}

export const csrfMiddleware: Middleware = {
  onRequest({ request }) {
    if (UNSAFE_METHODS.has(request.method)) {
      const token = readCookie("csrftoken");
      if (token) request.headers.set("X-CSRFToken", token);
    }
    return request;
  },
};

export const api = createClient<paths>({ baseUrl: "/", credentials: "same-origin" });
api.use(csrfMiddleware);

export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(status: number, body: unknown) {
    super(errorText(body) || `Request failed (${status})`);
    this.status = status;
    this.body = body;
  }
}

export function errorText(body: unknown): string {
  if (typeof body === "string") return body;
  if (Array.isArray(body)) return body.map(errorText).join(" ");
  if (body && typeof body === "object") {
    return Object.entries(body)
      .map(([field, value]) => {
        const text = errorText(value);
        return field === "detail" || field === "non_field_errors" ? text : `${field}: ${text}`;
      })
      .join(" ");
  }
  return "";
}

export async function unwrap<T>(
  call: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await call;
  if (!response.ok) throw new ApiError(response.status, error);
  return data as T;
}
