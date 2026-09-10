import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { EmptyState } from "./EmptyState";

afterEach(cleanup);

describe("EmptyState", () => {
  it("renders the title", () => {
    render(<EmptyState title="No agents yet" />);
    expect(screen.getByText("No agents yet")).toBeDefined();
  });

  it("renders an optional hint", () => {
    render(<EmptyState title="No agents yet" hint="Agents your team adds will show up here." />);
    expect(screen.getByText("Agents your team adds will show up here.")).toBeDefined();
  });

  it("omits the hint when none is given", () => {
    render(<EmptyState title="No agents yet" />);
    expect(screen.queryByText(/will show up here/)).toBeNull();
  });
});
