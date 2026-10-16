import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import "../../i18n";
import { StatusLine } from "./StatusLine";

describe("StatusLine", () => {
  it("shows a holiday with its names", () => {
    render(
      <StatusLine
        day={{
          date: "2027-03-23",
          is_business_day: false,
          reason: "holiday",
          holidays: ["Pakistan Day"],
          half_day: false,
        }}
      />,
    );
    expect(screen.getByText("Day off")).toBeInTheDocument();
    expect(screen.getByText("Public holiday")).toBeInTheDocument();
    expect(screen.getByText("Pakistan Day")).toBeInTheDocument();
  });

  it("labels a company half day as a business day", () => {
    render(
      <StatusLine
        day={{
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
