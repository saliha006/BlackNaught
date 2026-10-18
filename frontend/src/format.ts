export function formatElapsed(hours: number): string {
  const totalMin = Math.max(0, Math.round(hours * 60));
  if (totalMin < 60) return `${totalMin} min`;
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  return m === 0 ? `${h} h` : `${h} h ${m} min`;
}

export const formatCount = (n: number | null) => (n === null ? '–' : n.toLocaleString('en-GB'));
