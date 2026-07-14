const KST_DT = new Intl.DateTimeFormat("sv-SE", {
  timeZone: "Asia/Seoul",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

const KST_D = new Intl.DateTimeFormat("sv-SE", {
  timeZone: "Asia/Seoul",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

export function formatDateTimeKST(iso?: string | null): string {
  if (!iso) return "-";
  try {
    return `${KST_DT.format(new Date(iso))} KST`;
  } catch {
    return iso;
  }
}

export function formatDateKST(iso?: string | null): string {
  if (!iso) return "-";
  try {
    return KST_D.format(new Date(iso));
  } catch {
    return iso;
  }
}

export function nowIso(): string {
  return new Date().toISOString();
}

export function genId(prefix: string = "id"): string {
  return `${prefix}_${Date.now().toString(36)}_${Math.random()
    .toString(36)
    .slice(2, 8)}`;
}
