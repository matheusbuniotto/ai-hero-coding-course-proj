import { useEffect, useRef } from "react";

interface ResizeHandleProps {
  /** "vertical": drag left/right resizes width. "horizontal": drag up/down resizes height. */
  orientation: "vertical" | "horizontal";
  /** Called with the pointer's raw movement since the last event; sign is the caller's to interpret. */
  onDrag: (deltaPx: number) => void;
  label: string;
}

export function ResizeHandle({ orientation, onDrag, label }: ResizeHandleProps) {
  const draggingRef = useRef(false);
  const lastPosRef = useRef(0);
  const onDragRef = useRef(onDrag);
  onDragRef.current = onDrag;

  useEffect(() => {
    function handleMove(event: PointerEvent) {
      if (!draggingRef.current) return;
      const pos = orientation === "vertical" ? event.clientX : event.clientY;
      onDragRef.current(pos - lastPosRef.current);
      lastPosRef.current = pos;
    }
    function handleUp() {
      draggingRef.current = false;
      document.body.classList.remove("is-resizing");
    }
    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerup", handleUp);
    return () => {
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", handleUp);
      document.body.classList.remove("is-resizing");
    };
  }, [orientation]);

  function onPointerDown(event: React.PointerEvent) {
    draggingRef.current = true;
    lastPosRef.current = orientation === "vertical" ? event.clientX : event.clientY;
    document.body.classList.add("is-resizing");
  }

  return (
    <div
      className={`resize-handle resize-handle-${orientation}`}
      role="separator"
      aria-orientation={orientation}
      aria-label={label}
      onPointerDown={onPointerDown}
    />
  );
}
