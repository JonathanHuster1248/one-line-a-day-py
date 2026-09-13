import { useEffect, useState } from "react";
import { getGreeting, getJournal, getJournals, createJournalEntry } from "./greeting";

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
    const [message, setMessage] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

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

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!message.trim()) return;

        setIsSubmitting(true);
        try {
            await createJournalEntry(selectedDate, message);
            setMessage("");

            const [year, month, day] = selectedDate.split('-').map(Number);
            const updatedJournals = await getJournals(month, day);
            setJournals(updatedJournals);
        } catch (error) {
            console.error("Failed to create journal entry:", error);
        } finally {
            setIsSubmitting(false);
        }
    };
    
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
            <form onSubmit={handleSubmit} className="new-entry-form">
                <input
                    type="text"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="Write a new entry for this day..."
                    disabled={isSubmitting}
                />
                <button type="submit" disabled={isSubmitting || !message.trim()}>
                    {isSubmitting ? "Sending..." : "Send"}
                </button>
            </form>
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


