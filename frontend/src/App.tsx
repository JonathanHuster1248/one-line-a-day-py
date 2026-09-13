import { useEffect, useState } from "react";
import { getGreeting, getJournal, getJournals} from "./greeting";

export default function App() {
    // const [greeting, setGreeting] = useState("Loading...");
    const [journals, setJournals] = useState<Journal[] | null>(null)

    useEffect(() => {
        async function loadJournals() {
            try {
                // const journalId = "20f06456-00e3-47f8-a6e1-cbcb2d31bb20";
                // const journalData = await getJournal(journalId);
                const journals = await getJournals();

                setJournals(journals);
            } catch (error) {
                console.error("Failed to load journal:", error);
            }
        }

        loadJournals();
    }, []);
    
    if (journals === null) {
        return <div>Awaiting Entry</div>;
    }

    return (
        <div>
            {journals.map((journal) => (
                <JournalBox
                    key={journal.id}
                    journal={journal}
                />
            ))}
        </div>
    );

    // return (
    //     <div className="box">
    //         <h2>{entry.date}</h2>
    //         <p>{entry.message}</p>
    //     </div>
    // );
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


