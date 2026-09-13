// import { Journal } from "./models"

interface Journal {
    id: string;
    author_id: string;
    date: string;
    message: string;
}

export async function getGreeting(): Promise<string> {
    const response = await fetch("http://localhost:8000/hello_world");
    return await response.text();
}

export async function getJournal(id: string): Promise<Journal> {
    const response = await fetch(`http://localhost:8000/journals/${id}`);
    return await response.json() as Journal;
}

export async function getJournals(month?: number, day?: number, year?: number): Promise<Journal[]> {
    const id = "3665e0d9-efb8-4d0f-8ccd-a70f8a3a0e4a"
    const selectedMonth = month ?? 7
    const selectedDay = day ?? 25
    const selectedYear = year ?? new Date().getFullYear()

    let url = `http://localhost:8000/journals/?author_id=${id}&month=${selectedMonth}&day=${selectedDay}`;
    if (year !== undefined) {
        url += `&year=${selectedYear}`;
    }

    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(
            `Failed to load journals: ${response.status}`
        );
    }

    return (await response.json()) as Journal[];
}

export const DEFAULT_USER_ID = "3665e0d9-efb8-4d0f-8ccd-a70f8a3a0e4a";

export async function createJournalEntry(date: string, message: string): Promise<Journal> {
    const params = new URLSearchParams({
        author_id: DEFAULT_USER_ID,
        date: date,
        message: message,
    });

    const response = await fetch(`http://localhost:8000/journals/?${params.toString()}`, {
        method: "POST",
    });

    if (!response.ok) {
        throw new Error(
            `Failed to create journal entry: ${response.status}`
        );
    }

    return (await response.json()) as Journal;
}