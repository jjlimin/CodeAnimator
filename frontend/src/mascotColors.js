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

// Two-stop gradients + shadow tint per mascot color, for brand surfaces
// (buttons, flashcard back) that used to be hardcoded to the default orange.
// 'orange' matches the original hardcoded brand colors exactly, so picking
// the default keeps today's look pixel-for-pixel unchanged.
const GRADIENTS = {
  orange: { from: '#EA6F22', to: '#d35f1c', shadowRgb: '234,111,34' },
  purple: { from: '#a855f7', to: '#7c3aed', shadowRgb: '168,85,247' },
  blue:   { from: '#3b82f6', to: '#1d4ed8', shadowRgb: '59,130,246' },
  teal:   { from: '#14b8c4', to: '#0f766e', shadowRgb: '20,184,196' },
  green:  { from: '#22c55e', to: '#16a34a', shadowRgb: '34,197,94' },
  pink:   { from: '#ec4899', to: '#db2777', shadowRgb: '236,72,153' },
};

export const gradientForMascot = (key) => GRADIENTS[key] || GRADIENTS.orange;
