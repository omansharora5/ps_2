export type Focus = { lat: number; lon: number };
const RAD = Math.PI / 180;

export function longitudeDelta(from: number, to: number): number {
  return ((to - from + 540) % 360) - 180;
}

export function interpolateFocus(from: Focus, to: Focus, progress: number): Focus {
  const t = Math.max(0, Math.min(1, progress));
  return { lat: from.lat + (to.lat - from.lat) * t, lon: from.lon + longitudeDelta(from.lon, to.lon) * t };
}

export function projectPoint(lat: number, lon: number, focus: Focus) {
  const phi = lat * RAD;
  const phi0 = focus.lat * RAD;
  const lambda = (lon - focus.lon) * RAD;
  return {
    x: Math.cos(phi) * Math.sin(lambda),
    y: -(Math.cos(phi0) * Math.sin(phi) - Math.sin(phi0) * Math.cos(phi) * Math.cos(lambda)),
    z: Math.sin(phi0) * Math.sin(phi) + Math.cos(phi0) * Math.cos(phi) * Math.cos(lambda),
  };
}
