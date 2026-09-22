/**
 * Geometry from SoMaCoSF/hex-map-wfc HexTiles.getWorldPosition + NOTES.md
 * Cells: pointy-top. Offset: odd-r (stagger odd rows).
 * HEX_WIDTH = 2, HEX_HEIGHT = 4/sqrt(3)
 * Offset->axial: q = col - floor(row/2), r = row
 * Axial->offset: col = q + floor(r/2), row = r
 */
export const HEX_WIDTH = 2;
export const HEX_HEIGHT = (2 / Math.sqrt(3)) * 2;
export const CUBE_DIRS = [[1,0,-1],[1,-1,0],[0,-1,1],[-1,0,1],[-1,1,0],[0,1,-1]];

export function axialToOffset(q, r) {
  return { col: q + Math.floor(r / 2), row: r };
}
export function offsetToAxial(col, row) {
  return { q: col - Math.floor(row / 2), r: row, s: -(col - Math.floor(row / 2)) - row };
}
export function isInHexRadius(col, row, radius) {
  const r = row;
  const q = col - Math.floor(row / 2);
  if (q < -radius || q > radius) return false;
  const r1 = Math.max(-radius, -q - radius);
  const r2 = Math.min(radius, -q + radius);
  return r >= r1 && r <= r2;
}
/** Same as HexTileGeometry.getWorldPosition(gridX, gridZ). scale multiplies WU. */
export function getWorldPosition(gridX, gridZ, scale = 1) {
  const w = HEX_WIDTH * scale;
  const h = HEX_HEIGHT * scale;
  const x = gridX * w + (Math.abs(gridZ) % 2) * w * 0.5;
  const z = gridZ * h * 0.75;
  return { x, z };
}
export function cubeCells(radius) {
  const out = [];
  for (let q = -radius; q <= radius; q++) {
    const r1 = Math.max(-radius, -q - radius);
    const r2 = Math.min(radius, -q + radius);
    for (let r = r1; r <= r2; r++) out.push({ q, r, s: -q - r });
  }
  return out;
}
export function hexCornersPointy(x, z, size) {
  const pts = [];
  for (let i = 0; i < 6; i++) {
    const a = Math.PI / 180 * (60 * i - 30);
    pts.push([x + size * Math.cos(a), z + size * Math.sin(a)]);
  }
  return pts;
}
