import { translators, type Locale } from "./i18n";

export type Target = { slug: string; name: string; ra: number; dec: number; time: string };

export const CAPTURE_RADIUS = 5;
const RELEASE_RADIUS = 7;
const RAD = Math.PI / 180;
export const wrap = (angle: number) => ((angle % 360) + 360) % 360;
export const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
const raOffset = (from: number, to: number) => wrap(to - from + 180) - 180;

function separation(ra: number, dec: number, item: Target) {
  const chord = Math.sin((item.dec - dec) * RAD / 2) ** 2
    + Math.cos(dec * RAD) * Math.cos(item.dec * RAD) * Math.sin(raOffset(ra, item.ra) * RAD / 2) ** 2;
  return 2 * Math.asin(Math.sqrt(clamp(chord, 0, 1))) / RAD;
}

export function nearestTarget(ra: number, dec: number, targets: Target[], skip: (item: Target) => boolean) {
  let nearest: { item: Target; distance: number } | null = null;
  for (const item of targets) {
    if (skip(item)) continue;
    const distance = separation(ra, dec, item);
    if (!nearest || distance < nearest.distance) nearest = { item, distance };
  }
  return nearest;
}

export function scanPath(from: { ra: number; dec: number }, nextRA: number, nextDec: number, targets: Target[], locked: Target | null, raTravel?: number) {
  const deltaRA = raTravel ?? nextRA - from.ra;
  const deltaDec = nextDec - from.dec;
  // A slider jump can cross the capture zone without emitting a value inside it.
  const steps = Math.max(1, Math.ceil(Math.hypot(deltaRA, deltaDec)));
  let hit: Target | null = null;
  for (let step = 1; step <= steps; step++) {
    const fraction = step / steps;
    const ra = step === steps ? nextRA : wrap(from.ra + deltaRA * fraction);
    const dec = step === steps ? nextDec : from.dec + deltaDec * fraction;
    if (locked && separation(ra, dec, locked) > RELEASE_RADIUS) locked = null;
    if (!hit) {
      const nearest = nearestTarget(ra, dec, targets, (item) => item.slug === locked?.slug);
      if (nearest && nearest.distance <= CAPTURE_RADIUS) hit = nearest.item;
    }
    if (hit && !locked) break;
  }
  return { hit, locked };
}

export function axisHint(axis: string, offset: number, locale: Locale = "en") {
  const t = translators[locale];
  if (Math.abs(offset) <= 1) return t("{axis} no rumo", { axis });
  return t(offset > 0 ? "Aumente {axis}" : "Diminua {axis}", { axis });
}
