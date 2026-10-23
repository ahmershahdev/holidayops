import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { beforeAll, describe, expect, it } from "vitest";
import "../i18n";
import { Select } from "./Dropdown";

const COUNTRIES = [
  "Pakistan",
  "Peru",
  "Poland",
  "Portugal",
  "Qatar",
  "Romania",
  "Rwanda",
  "Samoa",
  "Saudi Arabia",
  "Senegal",
  "Serbia",
  "Singapore",
  "Slovakia",
  "Spain",
];

function Harness({ names }: { names: string[] }) {
  const [value, setValue] = useState(names[0] ?? "");
  return (
    <>
      <Select aria-label="Country" value={value} onChange={(e) => setValue(e.target.value)}>
        {names.map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
      </Select>
      <output>{value}</output>
    </>
  );
}

describe("Select", () => {
  beforeAll(() => {
    // jsdom has no layout.
    Element.prototype.scrollIntoView = () => undefined;
  });

  it("opens a listbox and picks with the keyboard", () => {
    render(<Harness names={["Free", "Pro", "Team"]} />);
    const trigger = screen.getByRole("button", { name: "Country" });
    expect(trigger).toHaveTextContent("Free");
    fireEvent.keyDown(trigger, { key: "ArrowDown" });
    const list = screen.getByRole("listbox");
    expect(screen.getByRole("option", { name: "Free" })).toHaveAttribute("aria-selected", "true");
    fireEvent.keyDown(list, { key: "ArrowDown" });
    fireEvent.keyDown(list, { key: "Enter" });
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Pro");
  });

  it("filters long lists by search, ignoring accents and case", () => {
    render(<Harness names={[...COUNTRIES, "Curaçao"]} />);
    fireEvent.click(screen.getByRole("button", { name: "Country" }));
    const search = screen.getByRole("combobox");
    fireEvent.change(search, { target: { value: "CURACAO" } });
    expect(screen.getAllByRole("option")).toHaveLength(1);
    fireEvent.keyDown(search, { key: "Enter" });
    expect(screen.getByRole("status")).toHaveTextContent("Curaçao");
  });

  it("closes on Escape without changing the value", () => {
    render(<Harness names={["Free", "Pro"]} />);
    fireEvent.click(screen.getByRole("button", { name: "Country" }));
    fireEvent.keyDown(screen.getByRole("listbox"), { key: "Escape" });
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Free");
  });
});
