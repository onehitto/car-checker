import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Odometer } from "./Odometer";
import { StatusBadge } from "./StatusBadge";

describe("Odometer", () => {
  it("exposes the reading to assistive technologies only once", () => {
    render(<Odometer value={98400} unit="km" label="98,400 km" />);
    expect(screen.getByRole("img", { name: "98,400 km" })).toBeInTheDocument();
  });

  it("pads to six drums and rolls each drum to its digit", () => {
    const { container } = render(<Odometer value={4205} unit="km" label="4,205 km" />);
    const strips = container.querySelectorAll<HTMLElement>("[style]");
    expect(strips).toHaveLength(6);
    expect(Array.from(strips, (strip) => strip.style.transform)).toEqual([
      "translateY(-0em)",
      "translateY(-0em)",
      "translateY(-4.6em)",
      "translateY(-2.3em)",
      "translateY(-0em)",
      "translateY(-5.75em)",
    ]);
  });
});

describe("StatusBadge", () => {
  it("shows the translated status label", () => {
    render(<StatusBadge status="due_soon" />);
    expect(screen.getByText("Due soon")).toBeInTheDocument();
  });
});
