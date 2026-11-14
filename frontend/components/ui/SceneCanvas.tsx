"use client";

import { useEffect, useRef, useState, type ComponentProps } from "react";
import { makeScene } from "../../lib/scene";

type Props = ComponentProps<"canvas"> & {
  ra: number;
  dec: number;
  time?: number;
  variant?: "lab" | "orbital";
};

export default function SceneCanvas({ ra, dec, time, variant = "lab", ...props }: Props) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const drawRef = useRef<() => void>(undefined);
  const angles = useRef({ ra, dec, time });
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const element = canvas.current;
    if (!element) return;
    const scene = makeScene(element, variant);
    if (!scene) {
      setFailed(true);
      return;
    }
    const draw = () => {
      const { ra, dec, time } = angles.current;
      scene.draw(element.clientWidth, element.clientHeight, ra, dec, time);
    };
    drawRef.current = draw;
    const resize = new ResizeObserver(draw);
    resize.observe(element);
    const texture = new window.Image();
    texture.onload = () => {
      scene.setTexture(texture);
      draw();
    };
    texture.src = "/laboratorio/blue-marble.jpg";
    draw();
    return () => {
      resize.disconnect();
      texture.onload = null;
      drawRef.current = undefined;
    };
  }, [variant]);

  useEffect(() => {
    angles.current = { ra, dec, time };
    drawRef.current?.();
  }, [ra, dec, time]);

  return (
    <>
      <canvas ref={canvas} {...props} />
      {failed && <p className="scene-message" role="status">Cena 3D indisponível. Os controles de coordenadas continuam disponíveis.</p>}
    </>
  );
}
