import { useEffect, useState } from "react";
import { getGreeting, getJournal, getJournals} from "./greeting";

export default function App() {
    // const [greeting, setGreeting] = useState("Loading...");
    const [journals, setJournals] = useState<Journal[] | null>(null)
    const [selectedDate, setSelectedDate] = useState<string>(() => {
        const today = new Date();
        const year = today.getFullYear();
        const month = String(today.getMonth() + 1).padStart(2, '0');
        const day = String(today.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    });

    useEffect(() => {
        async function loadJournals() {
            try {
                const [year, month, day] = selectedDate.split('-').map(Number);
                const journals = await getJournals(month, day);

                setJournals(journals);
            } catch (error) {
                console.error("Failed to load journal:", error);
            }
        }

        loadJournals();
    }, [selectedDate]);
    
    if (journals === null) {
        return <div>Awaiting Entry</div>;
    }

    return (
        <div>
            <div className="date-selector">
                <label htmlFor="date-input">Select Date: </label>
                <input
                    id="date-input"
                    type="date"
                    value={selectedDate}
                    onChange={(e) => setSelectedDate(e.target.value)}
                />
            </div>
            {journals.map((journal) => (
                <JournalBox
                    key={journal.id}
                    journal={journal}
                />
            ))}
        </div>
    );

}

function JournalBox({ journal }: { journal: Journal }) {
    return (
        <div className="box">
            <h2>{journal.date}</h2>
            <p>{journal.message}</p>
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


