import { useEffect, useState } from "react";
import { getGreeting, getJournal } from "./greeting";

export default function App() {
    // const [greeting, setGreeting] = useState("Loading...");
    const [entry, setEntry] = useState<Journal | null>(null)

    useEffect(() => {
        async function loadEntry() {
            try {
                const journalId = "20f06456-00e3-47f8-a6e1-cbcb2d31bb20";
                const journalData = await getJournal(journalId);

                setEntry(journalData);
            } catch (error) {
                console.error("Failed to load journal:", error);
            }
        }

        loadEntry();
    }, []);
    
    if (entry === null) {
        return <div>Awaiting Entry</div>;
    }

    return (
        <div className="box">
            <h2>{entry.date}</h2>
            <p>{entry.message}</p>
        </div>
    );
}

function makeEntryElement(date: string, message: string) {
    const entry = document.createElement("div");
    entry.className = "box";

    const dateElement = document.createElement("h2");
    dateElement.textContent = date;

    const messageElement = document.createElement("p");
    messageElement.textContent = message;

    entry.append(dateElement, messageElement)
    
    return entry
}


