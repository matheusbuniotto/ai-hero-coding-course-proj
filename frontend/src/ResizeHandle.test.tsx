import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResizeHandle } from "./ResizeHandle";

afterEach(cleanup);

describe("ResizeHandle", () => {
  it("reports the pointer's movement while dragging", () => {
    const onDrag = vi.fn();
    render(<ResizeHandle orientation="vertical" onDrag={onDrag} label="Resize chat" />);
    const handle = screen.getByRole("separator", { name: "Resize chat" });

    fireEvent.pointerDown(handle, { clientX: 100 });
    fireEvent.pointerMove(window, { clientX: 120 });
    expect(onDrag).toHaveBeenCalledWith(20);

    fireEvent.pointerMove(window, { clientX: 115 });
    expect(onDrag).toHaveBeenCalledWith(-5);
  });

  it("stops reporting movement after pointer up", () => {
    const onDrag = vi.fn();
    render(<ResizeHandle orientation="horizontal" onDrag={onDrag} label="Resize output" />);
    const handle = screen.getByRole("separator", { name: "Resize output" });

    fireEvent.pointerDown(handle, { clientY: 50 });
    fireEvent.pointerUp(window);
    fireEvent.pointerMove(window, { clientY: 80 });

    expect(onDrag).not.toHaveBeenCalled();
  });
});
