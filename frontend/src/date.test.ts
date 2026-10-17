import { describe, expect, it } from "vitest";
import { formatMonthDay, formatYear, shiftDate, shiftYear, toISODate } from "./date";

describe("toISODate", () => {
    it("pads single-digit months and days", () => {
        expect(toISODate(new Date(2026, 0, 5))).toBe("2026-01-05");
    });
});

describe("formatMonthDay", () => {
    it("formats as uppercase month name and day", () => {
        expect(formatMonthDay("2026-07-25")).toBe("JULY 25");
    });
});

describe("formatYear", () => {
    it("extracts the year from an ISO date string", () => {
        expect(formatYear("2026-07-25")).toBe("2026");
    });
});

describe("shiftDate", () => {
    it("moves forward across a month boundary", () => {
        expect(shiftDate("2026-01-31", 1)).toBe("2026-02-01");
    });

    it("moves backward across a year boundary", () => {
        expect(shiftDate("2026-01-01", -1)).toBe("2025-12-31");
    });
});

describe("shiftYear", () => {
    it("shifts the year while keeping month and day", () => {
        expect(shiftYear("2026-07-25", -1)).toBe("2025-07-25");
    });

    it("handles Feb 29 on a leap year shifting to a non-leap year", () => {
        expect(shiftYear("2024-02-29", 1)).toBe("2025-03-01");
    });
});
