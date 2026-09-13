import { API_BASE_URL } from "./config";

// import { Journal } from "./models"

interface Journal {
    id: string;
    author_id: string;
    date: string;
    message: string;
}

export async function getGreeting(): Promise<string> {
    const response = await fetch(`${API_BASE_URL}/hello_world`, { credentials: "include" });
    return await response.text();
}

export async function getJournal(id: string): Promise<Journal> {
    const response = await fetch(`${API_BASE_URL}/journals/${id}`, { credentials: "include" });
    return await response.json() as Journal;
}

export async function getJournals(month?: number, day?: number, year?: number): Promise<Journal[]> {
    const selectedMonth = month ?? 7
    const selectedDay = day ?? 25
    const selectedYear = year ?? new Date().getFullYear()

    let url = `${API_BASE_URL}/journals/?month=${selectedMonth}&day=${selectedDay}`;
    if (year !== undefined) {
        url += `&year=${selectedYear}`;
    }

    const response = await fetch(url, { credentials: "include" });

    if (!response.ok) {
        throw new Error(
            `Failed to load journals: ${response.status}`
        );
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

    if (!response.ok) {
        throw new Error(
            `Failed to create journal entry: ${response.status}`
        );
    }

    return (await response.json()) as Journal;
}
