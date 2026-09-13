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

export async function getJournals(): Promise<Journal[]> {
    const id = "3665e0d9-efb8-4d0f-8ccd-a70f8a3a0e4a"
    const month = 7
    const day = 25

    const response = await fetch(`http://localhost:8000/journals/?author_id=${id}&month=${month}&day=${day}`);

    if (!response.ok) {
        throw new Error(
            `Failed to load journals: ${response.status}`
        );
    }
    
    return (await response.json()) as Journal[];
}