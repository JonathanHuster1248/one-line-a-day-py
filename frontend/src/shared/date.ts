export function todayISODate(): string {
    return toISODate(new Date());
}

export function toISODate(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

export function formatMonthDay(dateStr: string): string {
    const [year, month, day] = dateStr.split("-").map(Number);
    const monthName = new Date(year, month - 1, day).toLocaleString("en-US", { month: "long" });
    return `${monthName.toUpperCase()} ${day}`;
}

export function formatYear(dateStr: string): string {
    return dateStr.split("-")[0];
}

export function shiftDate(dateStr: string, deltaDays: number): string {
    const [year, month, day] = dateStr.split("-").map(Number);
    const date = new Date(year, month - 1, day);
    date.setDate(date.getDate() + deltaDays);
    return toISODate(date);
}

export function shiftYear(dateStr: string, deltaYears: number): string {
    const [year, month, day] = dateStr.split("-").map(Number);
    const date = new Date(year, month - 1, day);
    date.setFullYear(date.getFullYear() + deltaYears);
    return toISODate(date);
}
