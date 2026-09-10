import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { Loading } from "./Loading";

afterEach(cleanup);

describe("Loading", () => {
  it("exposes itself as a labelled status region", () => {
    render(<Loading label="Loading proposals" />);
    expect(screen.getByRole("status", { name: "Loading proposals" })).toBeDefined();
  });

  it("renders the requested number of skeleton bars", () => {
    render(<Loading label="Loading history" lines={5} />);
    const status = screen.getByRole("status", { name: "Loading history" });
    expect(status.children).toHaveLength(5);
  });

  it("defaults to three skeleton bars", () => {
    render(<Loading label="Loading" />);
    const status = screen.getByRole("status", { name: "Loading" });
    expect(status.children).toHaveLength(3);
  });
});
