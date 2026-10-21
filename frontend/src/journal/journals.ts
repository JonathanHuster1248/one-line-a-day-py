import { API_BASE_URL } from "../shared/config";
import type { Journal } from "../shared/models";

/** The backend's 409: the user already has an entry on that date. */
export class DuplicateDateError extends Error {
    constructor() {
        super("You already have an entry for that date.");
        this.name = "DuplicateDateError";
    }
}

export async function getJournal(id: string): Promise<Journal> {
    const response = await fetch(`${API_BASE_URL}/journals/${id}`, { credentials: "include" });

    if (!response.ok) {
        throw new Error(`Failed to load journal entry: ${response.status}`);
    }

    return (await response.json()) as Journal;
}

export async function getJournals(month?: number, day?: number, year?: number): Promise<Journal[]> {
    const params = new URLSearchParams();
    if (month !== undefined) params.set("month", String(month));
    if (day !== undefined) params.set("day", String(day));
    if (year !== undefined) params.set("year", String(year));

    const response = await fetch(`${API_BASE_URL}/journals/?${params.toString()}`, {
        credentials: "include",
    });

    if (!response.ok) {
        throw new Error(`Failed to load journals: ${response.status}`);
    }

    return (await response.json()) as Journal[];
}

export async function createJournalEntry(date: string, message: string): Promise<Journal> {
    const params = new URLSearchParams({
        date: date,
        message: message,
    });

    const response = await fetch(`${API_BASE_URL}/journals/?${params.toString()}`, {
        method: "POST",
        credentials: "include",
    });

    if (response.status === 409) {
        throw new DuplicateDateError();
    }
    if (!response.ok) {
        throw new Error(`Failed to create journal entry: ${response.status}`);
    }

    return (await response.json()) as Journal;
}

export async function updateJournalEntry(id: string, date: string, message: string): Promise<Journal> {
    const params = new URLSearchParams({
        input_date: date,
        message: message,
    });

    const response = await fetch(`${API_BASE_URL}/journals/${id}?${params.toString()}`, {
        method: "PUT",
        credentials: "include",
    });

    if (response.status === 409) {
        throw new DuplicateDateError();
    }
    if (!response.ok) {
        throw new Error(`Failed to update journal entry: ${response.status}`);
    }

    return (await response.json()) as Journal;
}

export async function deleteJournalEntry(id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/journals/${id}`, {
        method: "DELETE",
        credentials: "include",
    });

    if (!response.ok) {
        throw new Error(`Failed to delete journal entry: ${response.status}`);
    }
}
