"use client";

import { useLocale } from "./LocaleProvider";

import { useEffect, useRef, useState, type ComponentProps } from "react";
import { makeScene } from "../../lib/scene";

type Props = ComponentProps<"canvas"> & {
  ra: number;
  dec: number;
  time?: number;
  variant?: "lab" | "orbital";
};

export default function SceneCanvas({ ra, dec, time, variant = "lab", ...props }: Props) {
  const { t } = useLocale();
  const north = t("NORTE");
  const canvas = useRef<HTMLCanvasElement>(null);
  const scheduleDrawRef = useRef<() => void>(undefined);
  const angles = useRef({ ra, dec, time });
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const element = canvas.current;
    if (!element) return;
    const scene = makeScene(element, variant, north);
    if (!scene) {
      setFailed(true);
      return;
    }
    let frame: number | undefined;
    const scheduleDraw = () => {
      if (frame !== undefined) return;
      frame = requestAnimationFrame(() => {
        frame = undefined;
        const { ra, dec, time } = angles.current;
        scene.draw(element.clientWidth, element.clientHeight, ra, dec, time);
      });
    };
    scheduleDrawRef.current = scheduleDraw;
    const resize = new ResizeObserver(scheduleDraw);
    resize.observe(element);
    const texture = new window.Image();
    texture.onload = () => {
      scene.setTexture(texture);
      scheduleDraw();
    };
    texture.src = "/laboratorio/blue-marble.jpg";
    scheduleDraw();
    return () => {
      resize.disconnect();
      texture.onload = null;
      if (frame !== undefined) cancelAnimationFrame(frame);
      scheduleDrawRef.current = undefined;
    };
  }, [variant, north]);

  useEffect(() => {
    angles.current = { ra, dec, time };
    scheduleDrawRef.current?.();
  }, [ra, dec, time]);

  return (
    <>
      <canvas ref={canvas} {...props} />
      {failed && <p className="scene-message" role="status">{t("Cena 3D indisponível. Os controles de coordenadas continuam disponíveis.")}</p>}
    </>
  );
}
