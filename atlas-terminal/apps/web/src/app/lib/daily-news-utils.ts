export function dateKey(value: Date): string {
  const year = value.getFullYear();
  const month = `${value.getMonth() + 1}`.padStart(2, "0");
  const day = `${value.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function parseDateKey(value: string): Date {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, (month || 1) - 1, day || 1);
}

export function addDays(base: string | Date, amount: number): string {
  const next = typeof base === "string" ? parseDateKey(base) : new Date(base);
  next.setDate(next.getDate() + amount);
  return dateKey(next);
}

export function todayKey(): string {
  return dateKey(new Date());
}

export function isSupportedDailyNewsDate(value: string, maxPastDays = 7): boolean {
  const target = parseDateKey(value);
  const today = parseDateKey(todayKey());
  const delta = Math.round((today.getTime() - target.getTime()) / 86_400_000);
  return delta >= 0 && delta <= maxPastDays;
}

export function formatNewsHeading(value: string): string {
  return parseDateKey(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "short",
  });
}
