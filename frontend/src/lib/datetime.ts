const BEIJING_TIME_ZONE = "Asia/Shanghai";

export function formatBeijingDateTime(value: string): string {
  const date = new Date(withUtcFallback(value));

  if (Number.isNaN(date.getTime())) {
    return value.replace("T", " ").replace(/\.\d+/, "").replace(/Z$/, "");
  }

  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: BEIJING_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).formatToParts(date);
  const byType = Object.fromEntries(parts.map((part) => [part.type, part.value]));

  return `${byType.year}-${byType.month}-${byType.day} ${byType.hour}:${byType.minute}:${byType.second}`;
}

function withUtcFallback(value: string) {
  const trimmed = value.trim();

  if (/[zZ]|[+-]\d{2}:?\d{2}$/.test(trimmed)) {
    return trimmed;
  }

  return `${trimmed}Z`;
}
