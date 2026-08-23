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