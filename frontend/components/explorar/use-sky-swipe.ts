import { useRef, type PointerEvent } from "react";

export function useSkySwipe(move: (direction: -1 | 1) => void) {
  const start = useRef<{ id: number; x: number; y: number } | null>(null);

  return {
    onPointerDown(event: PointerEvent<HTMLElement>) {
      if (event.pointerType !== "touch" && event.pointerType !== "pen") return;
      if (!event.isPrimary) return;
      event.currentTarget.setPointerCapture(event.pointerId);
      start.current = { id: event.pointerId, x: event.clientX, y: event.clientY };
    },
    onPointerUp(event: PointerEvent<HTMLElement>) {
      const origin = start.current;
      if (origin?.id !== event.pointerId) return;
      start.current = null;
      const dx = event.clientX - origin.x;
      if (Math.abs(dx) >= 36 && Math.abs(dx) > Math.abs(event.clientY - origin.y)) move(dx < 0 ? 1 : -1);
    },
    onLostPointerCapture() { start.current = null; },
  };
}
