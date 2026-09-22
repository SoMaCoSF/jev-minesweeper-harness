/**
 * Two lattices live here:
 * 1) hex-math / SonomaSays: FLAT-TOP lon/lat (Red Blob / MapLibre)
 * 2) hex-map-wfc rendering: POINTY-TOP odd-r offset — see hex-wfc-geom.js
 * Do not mix pixel formulas. Cube (q,r,s) is shared.
 */
export * from './hex-wfc-geom.js';
export function axialToCube(q, r) { return { q, r, s: -q - r }; }
export function cubeDistance(a, b) {
  return (Math.abs(a.q - b.q) + Math.abs(a.r - b.r) + Math.abs(a.s - b.s)) / 2;
}
