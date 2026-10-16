import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CheckResultView } from "./CheckResultView";

describe("CheckResultView", () => {
  it("shows a holiday with its names", () => {
    render(
      <CheckResultView
        result={{
          date: "2027-03-23",
          is_business_day: false,
          reason: "holiday",
          holidays: ["Pakistan Day"],
          half_day: false,
        }}
      />,
    );
    expect(screen.getByText("Not a business day")).toBeInTheDocument();
    expect(screen.getByText("Holiday")).toBeInTheDocument();
    expect(screen.getByText("Pakistan Day")).toBeInTheDocument();
  });

  it("labels a company half day", () => {
    render(
      <CheckResultView
        result={{
          date: "2027-03-23",
          is_business_day: true,
          reason: "half_day",
          holidays: ["Payroll"],
          half_day: true,
        }}
      />,
    );
    expect(screen.getByText("Business day")).toBeInTheDocument();
    expect(screen.getByText("Half day")).toBeInTheDocument();
  });
});
