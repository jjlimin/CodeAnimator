// Codima mascot colors. The mascot art is a raster (PNG embedded in an SVG
// pattern), so it can't be recolored by swapping fills — instead each color is
// a CSS `hue-rotate` filter applied to the <img>. The rotations below were
// calibrated against the mascot's base orange (hue ~20 deg); hue-rotate only
// shifts saturated pixels, so the eyes/shading stay correct.
export const MASCOT_COLORS = [
  { key: 'orange', label: 'Orange', filter: 'none',                          swatch: '#f59e0b' },
  { key: 'purple', label: 'Purple', filter: 'hue-rotate(255deg) saturate(1.05)', swatch: '#a855f7' },
  { key: 'blue',   label: 'Blue',   filter: 'hue-rotate(195deg) saturate(1.05)', swatch: '#3b82f6' },
  { key: 'teal',   label: 'Teal',   filter: 'hue-rotate(160deg) saturate(1.05)', swatch: '#14b8c4' },
  { key: 'green',  label: 'Green',  filter: 'hue-rotate(100deg) saturate(1.05)', swatch: '#22c55e' },
  { key: 'pink',   label: 'Pink',   filter: 'hue-rotate(305deg) saturate(1.05)', swatch: '#ec4899' },
];

export const DEFAULT_MASCOT_COLOR = 'orange';

const KEYS = new Set(MASCOT_COLORS.map((c) => c.key));

// True only for values we recognize (guards against a junk zoneinfo value).
export const isMascotColor = (key) => KEYS.has(key);

export const filterForMascot = (key) =>
  MASCOT_COLORS.find((c) => c.key === key)?.filter || 'none';

export const swatchForMascot = (key) =>
  MASCOT_COLORS.find((c) => c.key === key)?.swatch || '#f59e0b';
