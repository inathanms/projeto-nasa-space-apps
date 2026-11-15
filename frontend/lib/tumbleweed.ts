const step = 1 / 30;

// Motion is sampled once, so the browser can play the transforms without a JS frame loop.
export function tumbleweedRoll(duration: number, gustDuration: number, gustForce: number) {
  const samples = [];
  let distance = 0;
  let speed = 0;
  let height = 0;
  let lift = 0;
  let bump = 0;
  const bumps = [0.22, 0.64, 1.1];

  for (let frame = 0; frame <= Math.round(duration / step); frame++) {
    const time = frame * step;
    samples.push({ time, distance, height });

    // The gust builds and tapers off. Drag and ground friction dissipate its momentum.
    const pressure = Math.sin(Math.PI * Math.min(time / gustDuration, 1)) ** 2;
    const friction = height === 0 ? 0.38 : 0;
    const acceleration = gustForce * pressure - speed * 1.45 - friction;
    speed = Math.max(0, speed + acceleration * step);
    distance += speed * step;

    if (bump < bumps.length && distance >= bumps[bump] && height === 0 && speed > 0.5) {
      lift = Math.min(1.8, speed * 1.05);
      bump++;
    }
    if (height > 0 || lift > 0) {
      lift -= 7 * step;
      height += lift * step;
      if (height <= 0) {
        height = 0;
        lift = lift < -0.85 ? -lift * 0.32 : 0;
      }
    }
  }

  return samples.map((sample) => ({
    time: sample.time,
    progress: sample.distance / distance,
    height: sample.height,
  }));
}
