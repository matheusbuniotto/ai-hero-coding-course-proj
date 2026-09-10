import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { DiffView } from "./DiffView";

afterEach(cleanup);

describe("DiffView", () => {
  it("shows the file path and expands by default", () => {
    render(<DiffView path="src/foo.ts" base={"a\nb"} proposed={"a\nb"} />);
    expect(screen.getByText("src/foo.ts")).toBeDefined();
    const toggle = screen.getByRole("button", { name: /src\/foo\.ts/ });
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
  });

  it("collapses and expands independently when toggled", () => {
    render(<DiffView path="src/foo.ts" base="a" proposed="b" />);
    const toggle = screen.getByRole("button", { name: /src\/foo\.ts/ });

    fireEvent.click(toggle);
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByText("a")).toBeNull();

    fireEvent.click(toggle);
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByText("a")).toBeDefined();
  });

  it("shows old and new line numbers for context, added, and removed lines", () => {
    render(<DiffView path="src/foo.ts" base={"a\nb\nc"} proposed={"a\nx\nc"} />);
    const lines = screen.getAllByRole("listitem");
    expect(lines).toHaveLength(4);

    function nums(line: HTMLElement) {
      const [oldNum, newNum] = line.querySelectorAll(".diff-line-num");
      return { old: oldNum.textContent, new: newNum.textContent };
    }

    // context "a": old 1, new 1
    expect(nums(lines[0])).toEqual({ old: "1", new: "1" });
    expect(lines[0].textContent).toContain("a");

    // removed "b": old 2, new number blank
    expect(nums(lines[1])).toEqual({ old: "2", new: "" });
    expect(lines[1].textContent).toContain("b");

    // added "x": old number blank, new 2
    expect(nums(lines[2])).toEqual({ old: "", new: "2" });
    expect(lines[2].textContent).toContain("x");

    // context "c": old 3, new 3
    expect(nums(lines[3])).toEqual({ old: "3", new: "3" });
    expect(lines[3].textContent).toContain("c");
  });

  it("collapses each file independently in a multi-file list", () => {
    render(
      <ul>
        <li>
          <DiffView path="src/a.ts" base="a" proposed="a2" />
        </li>
        <li>
          <DiffView path="src/b.ts" base="b" proposed="b2" />
        </li>
      </ul>,
    );
    const toggleA = screen.getByRole("button", { name: /src\/a\.ts/ });
    const toggleB = screen.getByRole("button", { name: /src\/b\.ts/ });

    fireEvent.click(toggleA);

    expect(toggleA.getAttribute("aria-expanded")).toBe("false");
    expect(toggleB.getAttribute("aria-expanded")).toBe("true");
    expect(screen.queryByText("a")).toBeNull();
    expect(screen.getByText("b")).toBeDefined();
  });

  it("renders header actions alongside the path without nesting inside the toggle button", () => {
    render(
      <DiffView
        path="src/foo.ts"
        base="a"
        proposed="b"
        headerActions={<span data-testid="extra">approved</span>}
      />,
    );
    expect(screen.getByTestId("extra")).toBeDefined();
  });
});
