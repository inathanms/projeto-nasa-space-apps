import { useEffect, useRef, useState, type CSSProperties, type KeyboardEvent, type MouseEvent, type PointerEvent } from "react";

type Point = { x: number; y: number };
type View = Point & { zoom: number };

const initial: View = { x: 0, y: 0, zoom: 1 };
const center: Point = { x: .5, y: .5 };
const arrows: Record<string, Point | undefined> = {
  ArrowLeft: { x: .12, y: 0 },
  ArrowRight: { x: -.12, y: 0 },
  ArrowUp: { x: 0, y: .12 },
  ArrowDown: { x: 0, y: -.12 },
};

function pointIn(element: HTMLElement, x: number, y: number): Point {
  const box = element.getBoundingClientRect();
  return { x: (x - box.left) / box.width, y: (y - box.top) / box.height };
}

function bound(x: number, y: number, zoom: number): View {
  return zoom === 1 ? initial : {
    x: Math.max(1 - zoom, Math.min(0, x)),
    y: Math.max(1 - zoom, Math.min(0, y)),
    zoom,
  };
}

function zoomFrom(view: View, amount: number, from: Point, to = from): View {
  const zoom = Math.max(1, Math.min(4, amount));
  const ratio = zoom / view.zoom;
  return bound(to.x - (from.x - view.x) * ratio, to.y - (from.y - view.y) * ratio, zoom);
}

function midpoint(a: Point, b: Point): Point {
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
}

export function useSkyViewport(active: boolean, changeEpoch?: (direction: -1 | 1) => void) {
  const ref = useRef<HTMLElement>(null);
  const pointers = useRef(new Map<number, Point>());
  const swipe = useRef<{ id: number; x: number; y: number } | null>(null);
  const [view, setView] = useState(initial);

  useEffect(() => {
    const element = ref.current;
    if (!active || !element) return;
    const activePointers = pointers.current;

    const wheel = (event: WheelEvent) => {
      if (!event.ctrlKey && !event.metaKey) return;
      event.preventDefault();
      const anchor = pointIn(element, event.clientX, event.clientY);
      const delta = event.deltaMode === 0 ? event.deltaY : event.deltaY * 16;
      setView((current) => zoomFrom(current, current.zoom * Math.exp(-delta * .012), anchor));
    };

    element.addEventListener("wheel", wheel, { passive: false });
    return () => {
      activePointers.clear();
      swipe.current = null;
      element.removeEventListener("wheel", wheel);
    };
  }, [active]);

  function forgetPointer(id: number) {
    pointers.current.delete(id);
    if (swipe.current?.id === id) swipe.current = null;
  }

  function adjustZoom(amount: number) {
    setView((current) => zoomFrom(current, current.zoom + amount, center));
  }

  return {
    ref,
    zoom: view.zoom,
    reset() {
      pointers.current.clear();
      swipe.current = null;
      setView(initial);
    },
    adjustZoom,
    props: {
      "data-zoomed": active && view.zoom > 1,
      style: {
        "--sky-zoom": view.zoom,
        "--sky-x": `${view.x * 100}%`,
        "--sky-y": `${view.y * 100}%`,
      } as CSSProperties,
      onDoubleClick(event: MouseEvent<HTMLElement>) {
        if (!active) return;
        const anchor = pointIn(event.currentTarget, event.clientX, event.clientY);
        setView((current) => current.zoom >= 4 ? initial : zoomFrom(current, current.zoom + 1, anchor));
      },
      onPointerDown(event: PointerEvent<HTMLElement>) {
        if (!active || (event.pointerType === "mouse" && (event.button !== 0 || view.zoom === 1))) return;
        const points = pointers.current;
        if (points.size >= 2) return;
        points.set(event.pointerId, pointIn(event.currentTarget, event.clientX, event.clientY));
        event.currentTarget.setPointerCapture(event.pointerId);
        swipe.current = points.size === 1 && view.zoom === 1
          ? { id: event.pointerId, x: event.clientX, y: event.clientY } : null;
      },
      onPointerMove(event: PointerEvent<HTMLElement>) {
        const points = pointers.current;
        const old = points.get(event.pointerId);
        if (!old) return;
        const next = pointIn(event.currentTarget, event.clientX, event.clientY);
        points.set(event.pointerId, next);
        const other = [...points].find(([id]) => id !== event.pointerId)?.[1];
        if (other) {
          const distance = Math.hypot(old.x - other.x, old.y - other.y);
          if (distance > .001) {
            const factor = Math.hypot(next.x - other.x, next.y - other.y) / distance;
            setView((current) => zoomFrom(current, current.zoom * factor, midpoint(old, other), midpoint(next, other)));
          }
        } else if (view.zoom > 1) {
          setView((current) => bound(current.x + next.x - old.x, current.y + next.y - old.y, current.zoom));
        }
      },
      onPointerUp(event: PointerEvent<HTMLElement>) {
        const start = swipe.current;
        forgetPointer(event.pointerId);
        if (start?.id !== event.pointerId || view.zoom > 1) return;
        const dx = event.clientX - start.x;
        if (Math.abs(dx) >= 36 && Math.abs(dx) > Math.abs(event.clientY - start.y)) changeEpoch?.(dx < 0 ? 1 : -1);
      },
      onLostPointerCapture(event: PointerEvent<HTMLElement>) { forgetPointer(event.pointerId); },
      onPointerCancel(event: PointerEvent<HTMLElement>) { forgetPointer(event.pointerId); },
      onKeyDown(event: KeyboardEvent<HTMLElement>) {
        if (event.ctrlKey || event.metaKey || event.altKey) return;
        const pan = arrows[event.key];
        if (active && (event.key === "+" || event.key === "=" || event.key === "-" || event.key === "0")) {
          event.preventDefault();
          if (event.key === "0") setView(initial);
          else adjustZoom(event.key === "-" ? -1 : 1);
        } else if (active && view.zoom > 1 && pan) {
          event.preventDefault();
          setView((current) => bound(current.x + pan.x, current.y + pan.y, current.zoom));
        } else if (changeEpoch && (event.key === "ArrowLeft" || event.key === "ArrowRight")) {
          event.preventDefault();
          changeEpoch(event.key === "ArrowLeft" ? -1 : 1);
        }
      },
    },
  };
}
