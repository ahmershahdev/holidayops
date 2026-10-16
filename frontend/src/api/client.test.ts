import { describe, expect, it } from "vitest";
import { ApiError, csrfMiddleware, errorText, readCookie } from "./client";

describe("readCookie", () => {
  it("finds a cookie among others", () => {
    expect(readCookie("csrftoken", "a=1; csrftoken=abc%3D; b=2")).toBe("abc=");
    expect(readCookie("missing", "a=1")).toBeNull();
  });
});

describe("csrfMiddleware", () => {
  const run = async (method: string) => {
    document.cookie = "csrftoken=tok123";
    const request = new Request("http://localhost/api/v1/orgs/", { method });
    const onRequest = csrfMiddleware.onRequest;
    if (!onRequest) throw new Error("middleware has no onRequest");
    const result = (await onRequest({ request } as Parameters<typeof onRequest>[0])) as Request;
    return result.headers.get("X-CSRFToken");
  };

  it("adds the token to unsafe methods only", async () => {
    expect(await run("POST")).toBe("tok123");
    expect(await run("DELETE")).toBe("tok123");
    expect(await run("GET")).toBeNull();
  });
});

describe("errorText", () => {
  it("flattens DRF error bodies", () => {
    expect(errorText({ email: ["Already used."] })).toBe("email: Already used.");
    expect(errorText({ non_field_errors: ["Bad login."] })).toBe("Bad login.");
    expect(errorText({ detail: "Not found." })).toBe("Not found.");
    expect(new ApiError(500, undefined).message).toBe("Request failed (500)");
  });
});
