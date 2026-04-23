/**
 * Compact 12-stop magma colormap. Values returned are [R,G,B] in 0–255.
 *
 * Stops sampled from the matplotlib magma cmap (Apache-2.0).
 */

const STOPS: [number, number, number][] = [
  [0, 0, 4],
  [24, 15, 61],
  [68, 15, 118],
  [114, 31, 129],
  [158, 47, 127],
  [205, 64, 113],
  [241, 96, 93],
  [254, 138, 81],
  [254, 180, 88],
  [253, 219, 109],
  [252, 253, 191],
  [255, 255, 255],
];

export function magma(t: number): [number, number, number] {
  const u = Math.max(0, Math.min(1, t));
  const scaled = u * (STOPS.length - 1);
  const i = Math.floor(scaled);
  const f = scaled - i;
  if (i >= STOPS.length - 1) return STOPS[STOPS.length - 1];
  const [r0, g0, b0] = STOPS[i];
  const [r1, g1, b1] = STOPS[i + 1];
  return [
    Math.round(r0 + (r1 - r0) * f),
    Math.round(g0 + (g1 - g0) * f),
    Math.round(b0 + (b1 - b0) * f),
  ];
}
