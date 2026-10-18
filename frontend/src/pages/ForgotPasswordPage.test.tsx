import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import "../i18n";
import { CodeInput, ForgotPasswordPage } from "./ForgotPasswordPage";

function Harness() {
  const [code, setCode] = useState("");
  return <CodeInput value={code} onChange={setCode} />;
}

describe("ForgotPasswordPage", () => {
  it("starts with the email step, prefilled from the login form", () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={["/forgot-password?email=sam%40example.com"]}>
          <ForgotPasswordPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(screen.getByRole("heading", { name: "Reset your password" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toHaveValue("sam@example.com");
    expect(screen.getByRole("button", { name: /Send code/ })).toBeInTheDocument();
  });

  it("keeps only six digits in the code field", () => {
    render(<Harness />);
    const input = screen.getByLabelText("6-digit code");
    fireEvent.change(input, { target: { value: "12a3-45678" } });
    expect(input).toHaveValue("123456");
    expect(input).toHaveAttribute("autocomplete", "one-time-code");
  });
});
