export function formatElapsed(hours: number): string {
  const totalMin = Math.max(0, Math.round(hours * 60));
  if (totalMin < 60) return `${totalMin} min`;
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  return m === 0 ? `${h} h` : `${h} h ${m} min`;
}

export const formatAgo = (seconds: number) =>
  seconds < 120 ? `${seconds} s ago` : `${Math.round(seconds / 60)} min ago`;

export const formatCount = (n: number | null) => (n === null ? '–' : n.toLocaleString('en-GB'));

const HTML_ESCAPES: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

/** For API strings that land inside an HTML template: the feeds are outside our control, so nothing in them may become markup. */
export const escapeHtml = (text: string) => text.replace(/[&<>"']/g, (c) => HTML_ESCAPES[c]);
