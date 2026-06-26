export function formatDate(iso?: string): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function formatRelative(iso?: string): string {
  if (!iso) return "—";
  const diff = new Date(iso).getTime() - Date.now();
  const days = Math.round(diff / (1000 * 60 * 60 * 24));
  if (days === 0) return "today";
  if (days > 0) return `in ${days}d`;
  return `${Math.abs(days)}d overdue`;
}

export function familyLabel(f: string): string {
  switch (f) {
    case "battery":
      return "EU Battery";
    case "reach":
      return "REACH";
    case "rohs":
      return "RoHS";
    case "weee":
      return "WEEE";
    default:
      return f;
  }
}
