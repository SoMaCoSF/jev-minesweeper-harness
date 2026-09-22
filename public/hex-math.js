/**
 * Hex grid math (axial + cube).
 * Flat-top, MapLibre / Red Blob. Origin default: Sonoma (-122.7, 38.45), 500m.
 * https://www.redblobgames.com/grids/hexagons/
 */
export function axialToCube(q, r) { return { q, r, s: -q - r }; }
export function cubeToAxial(q, r, s) { return { q, r }; }
export function cubeDistance(a, b) {
  return (Math.abs(a.q - b.q) + Math.abs(a.r - b.r) + Math.abs(a.s - b.s)) / 2;
}
export function lonLatToAxial(lon, lat, opts = {}) {
  const originLon = opts.originLon ?? -122.7;
  const originLat = opts.originLat ?? 38.45;
  const size = opts.hexSizeMeters ?? 500;
  const mPerDegLat = 111320;
  const mPerDegLon = 111320 * Math.cos((originLat * Math.PI) / 180);
  const x = (lon - originLon) * mPerDegLon;
  const y = (lat - originLat) * mPerDegLat;
  const q = ((2 / 3) * x) / size;
  const r = ((-1 / 3) * x + (Math.sqrt(3) / 3) * y) / size;
  return axialRound(q, r);
}
export function axialRound(q, r) {
  const s = -q - r;
  let rq = Math.round(q), rr = Math.round(r), rs = Math.round(s);
  const dq = Math.abs(rq - q), dr = Math.abs(rr - r), ds = Math.abs(rs - s);
  if (dq > dr && dq > ds) rq = -rr - rs;
  else if (dr > ds) rr = -rq - rs;
  return { q: rq, r: rr };
}
export function axialToLonLat(q, r, opts = {}) {
  const originLon = opts.originLon ?? -122.7;
  const originLat = opts.originLat ?? 38.45;
  const size = opts.hexSizeMeters ?? 500;
  const x = size * ((3 / 2) * q);
  const y = size * ((Math.sqrt(3) / 2) * q + Math.sqrt(3) * r);
  const mPerDegLat = 111320;
  const mPerDegLon = 111320 * Math.cos((originLat * Math.PI) / 180);
  return { lon: originLon + x / mPerDegLon, lat: originLat + y / mPerDegLat };
}
export function axialToPixel(q, r, size) {
  return { x: size * (3 / 2) * q, y: size * (Math.sqrt(3) / 2 * q + Math.sqrt(3) * r) };
}
export function hexCornersFlat(x, y, size) {
  const pts = [];
  for (let i = 0; i < 6; i++) {
    const a = (Math.PI / 180) * (60 * i);
    pts.push([x + size * Math.cos(a), y + size * Math.sin(a)]);
  }
  return pts;
}
export const CUBE_DIRS = [[1,0,-1],[1,-1,0],[0,-1,1],[-1,0,1],[-1,1,0],[0,1,-1]];
