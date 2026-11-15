"use client";

import { useEffect, useEffectEvent, useRef } from "react";
import { tumbleweedRoll } from "../../lib/tumbleweed";
import { useHeroMotion } from "./HeroMotion";
import s from "./landing.module.css";

// Galhos gerados de forma determinística (mesmo resultado no build e no cliente).
const galhos = Array.from({ length: 14 }, (_, i) => {
  const ang = (i * 360) / 14 + (i % 3) * 9;
  const rx = 30 - (i % 4) * 4;
  const ry = 12 + (i % 5) * 3;
  return { ang, rx, ry, cor: i % 3 === 0 ? "#e2b778" : i % 3 === 1 ? "#b9864c" : "#8d5f30" };
});

const cycle = 18;
const advanceStart = 0.34;
const retreatStart = 8.2;
const retreat = tumbleweedRoll(3.8, 1.4, 6.1);
const advance = tumbleweedRoll(3.6, 1.65, 5);
const path = [
  { time: 0, progress: 0, height: 0 },
  ...advance.map((sample) => ({ ...sample, time: advanceStart + sample.time })),
  ...retreat.map((sample) => ({
    ...sample,
    time: retreatStart + sample.time,
    progress: 1 - sample.progress,
  })),
  { time: cycle, progress: 0, height: 0 },
];

function windKeyframes(start: number, direction: 1 | -1, travel: number, center: number): Keyframe[] {
  const origin = direction === 1 ? 0 : travel;
  const gust = [
    { time: -0.22, progress: -0.1, opacity: 0 },
    { time: 0.7, progress: 0.17, opacity: 0.85 },
    { time: 1.4, progress: 0.52, opacity: 0.63 },
    { time: 2.25, progress: 0.83, opacity: 0 },
  ];
  return gust.map(({ time, progress, opacity }) => {
    const position = origin + direction * travel * progress + center;
    return {
      offset: (start + time) / cycle,
      transform: `translateX(calc(${position}px - 50%)) scaleX(${-direction})`,
      opacity,
    };
  });
}

export default function Tumbleweed() {
  const { paused } = useHeroMotion();
  const playback = useRef<() => void>(undefined);
  const motionEnabled = useEffectEvent(() => !paused);
  const strip = useRef<HTMLDivElement>(null);
  const lane = useRef<HTMLDivElement>(null);
  const shadow = useRef<HTMLDivElement>(null);
  const hop = useRef<HTMLDivElement>(null);
  const spin = useRef<HTMLDivElement>(null);
  const wind = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const scene = strip.current;
    const track = lane.current;
    const ground = shadow.current;
    const lift = hop.current;
    const roll = spin.current;
    const gust = wind.current;
    if (!scene || !track || !ground || !lift || !roll || !gust) return;

    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    let animations: Animation[] = [];
    let visible = false;
    let previousTravel = 0;
    let previousRadius = 0;

    function updatePlayback() {
      for (const animation of animations) {
        if (visible && !document.hidden && motionEnabled()) animation.play();
        else animation.pause();
      }
    }

    playback.current = updatePlayback;
    const build = () => {
      if (motion.matches) {
        animations.forEach((animation) => animation.cancel());
        animations = [];
        return;
      }

      const size = track.offsetWidth;
      const radius = size * 0.35;
      const travel = Math.max(0, scene.clientWidth - size);
      if (animations.length && travel === previousTravel && radius === previousRadius) return;
      previousTravel = travel;
      previousRadius = radius;

      const time = animations[0]?.currentTime ?? 0;
      animations.forEach((animation) => animation.cancel());

      const options = { duration: cycle * 1000, iterations: Infinity, fill: "both" } as const;
      animations = [
        track.animate(path.map(({ time, progress }) => ({
          offset: time / cycle,
          transform: `translateX(${progress * travel}px)`,
        })), options),
        roll.animate(path.map(({ time, progress }) => ({
          offset: time / cycle,
          transform: `rotate(${25 + progress * travel / radius * 180 / Math.PI}deg)`,
        })), options),
        lift.animate(path.map(({ time, height }) => ({
          offset: time / cycle,
          transform: `translateY(${-height * radius * 2.7}px)`,
        })), options),
        ground.animate(path.map(({ time, height }) => ({
          offset: time / cycle,
          transform: `scaleX(${1 - height * 0.85})`,
          opacity: 1 - height * 1.1,
        })), options),
        gust.animate([
          { offset: 0, opacity: 0 },
          ...windKeyframes(advanceStart, 1, travel, size / 2),
          ...windKeyframes(retreatStart, -1, travel, size / 2),
          { offset: 1, opacity: 0 },
        ], options),
      ];
      for (const animation of animations) animation.currentTime = time;
      updatePlayback();
    };

    const intersection = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      updatePlayback();
    });
    const resize = new ResizeObserver(build);
    intersection.observe(scene);
    resize.observe(scene);
    motion.addEventListener("change", build);
    document.addEventListener("visibilitychange", updatePlayback);
    build();

    return () => {
      intersection.disconnect();
      resize.disconnect();
      motion.removeEventListener("change", build);
      document.removeEventListener("visibilitychange", updatePlayback);
      playback.current = undefined;
      animations.forEach((animation) => animation.cancel());
    };
  }, []);

  useEffect(() => { playback.current?.(); }, [paused]);

  return (
    <div className={s.tumbleStrip} aria-hidden="true" ref={strip}>
      <div className={s.tumbleWind} ref={wind}>
        <svg viewBox="0 0 220 70" width="100%" focusable="false">
          <g fill="none" stroke="#ffe0ac" strokeLinecap="round">
            <path opacity=".46" d="M213 12Q183 9 161 18T108 24" />
            <path opacity=".72" strokeWidth="1.4" d="M196 31Q166 26 137 36T61 40" />
            <path opacity=".46" d="M151 51Q117 47 96 54T22 57M75 31Q57 34 36 31" />
          </g>
          <g fill="#ffd59a">
            <ellipse cx="128" cy="61" rx="4" ry="1.2" />
            <ellipse cx="97" cy="65" rx="2" ry="1" />
            <ellipse cx="49" cy="52" rx="2.6" ry="1" />
            <ellipse cx="13" cy="58" rx="1.6" ry=".8" />
          </g>
        </svg>
      </div>
      <div className={s.tumbleLane} ref={lane}>
        <div className={s.tumbleShadow} ref={shadow} />
        <div className={s.tumbleHop} ref={hop}>
          <div className={s.tumbleSpin} ref={spin}>
            <svg viewBox="-40 -40 80 80" width="100%" height="100%" focusable="false">
              <circle r={30} fill="#8d5f30" opacity={0.18} />
              <g fill="none" strokeWidth={1.6} strokeLinecap="round">
                {galhos.map((g, i) => (
                  <ellipse
                    key={i}
                    rx={g.rx}
                    ry={g.ry}
                    stroke={g.cor}
                    transform={`rotate(${g.ang})`}
                  />
                ))}
                <path
                  d="M-26 -8 Q-10 -24 6 -14 T28 -4 M-22 14 Q-4 2 12 18 T24 10 M-8 -28 Q4 -6 -6 10 T2 28 M10 -26 Q18 -4 4 8 T-14 24"
                  stroke="#c99a5e"
                />
              </g>
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}
