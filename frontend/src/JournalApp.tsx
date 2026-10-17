import { useEffect, useState } from "react";
import { getJournals, createJournalEntry, updateJournalEntry, deleteJournalEntry } from "./journals";
import type { Journal } from "./models";
import { useAuth } from "./AuthContext";
import { JournalBox } from "./JournalBox";
import { formatMonthDay, shiftDate, shiftYear, todayISODate } from "./date";

export function JournalApp() {
    const { logout } = useAuth();
    const [journals, setJournals] = useState<Journal[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [selectedDate, setSelectedDate] = useState<string>(todayISODate);
    const [message, setMessage] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let isCurrent = true;

        async function loadJournals() {
            setIsLoading(true);
            try {
                const [, month, day] = selectedDate.split("-").map(Number);
                const fetchedJournals = await getJournals(month, day);
                if (isCurrent) setJournals(fetchedJournals);
            } catch (error) {
                console.error("Failed to load journal:", error);
                if (isCurrent) setError("Failed to load entries for this day.");
            } finally {
                if (isCurrent) setIsLoading(false);
            }
        }

        loadJournals();
        return () => {
            isCurrent = false;
        };
    }, [selectedDate]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!message.trim()) return;

        setIsSubmitting(true);
        setError(null);
        try {
            const created = await createJournalEntry(selectedDate, message);
            setJournals((prev) => [...prev, created]);
            setMessage("");
        } catch (error) {
            console.error("Failed to create journal entry:", error);
            setError("Failed to save entry. Please try again.");
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleUpdate = async (journal: Journal, date: string, message: string) => {
        const updated = await updateJournalEntry(journal.id, date, message);
        setJournals((prev) => prev.map((j) => (j.id === updated.id ? updated : j)));
    };

    const handleDelete = async (journal: Journal) => {
        await deleteJournalEntry(journal.id);
        setJournals((prev) => prev.filter((j) => j.id !== journal.id));
    };

    if (isLoading) {
        return <div>Loading...</div>;
    }

    return (
        <div className="page-backdrop">
            <div className="journal-page">
                <div className="page-header">
                    <div className="date-selector">
                        <label htmlFor="date-input">Select Date: </label>
                        <input
                            id="date-input"
                            type="date"
                            value={selectedDate}
                            onChange={(e) => setSelectedDate(e.target.value)}
                        />
                    </div>
                    <button type="button" className="logout-button" onClick={() => logout()}>Log Out</button>
                </div>
                <div className="page-title-row">
                    <button
                        type="button"
                        className="date-nav-button"
                        aria-label="Previous year"
                        onClick={() => setSelectedDate(shiftYear(selectedDate, -1))}
                    >
                        &#8676;
                    </button>
                    <button
                        type="button"
                        className="date-nav-button"
                        aria-label="Previous day"
                        onClick={() => setSelectedDate(shiftDate(selectedDate, -1))}
                    >
                        &#8592;
                    </button>
                    <h1 className="page-title">{formatMonthDay(selectedDate)}</h1>
                    <button
                        type="button"
                        className="date-nav-button"
                        aria-label="Next day"
                        onClick={() => setSelectedDate(shiftDate(selectedDate, 1))}
                    >
                        &#8594;
                    </button>
                    <button
                        type="button"
                        className="date-nav-button"
                        aria-label="Next year"
                        onClick={() => setSelectedDate(shiftYear(selectedDate, 1))}
                    >
                        &#8677;
                    </button>
                </div>
                {error && <p className="page-error">{error}</p>}
                <div className="entries">
                    {journals.map((journal) => (
                        <JournalBox
                            key={journal.id}
                            journal={journal}
                            onUpdate={handleUpdate}
                            onDelete={handleDelete}
                        />
                    ))}
                </div>
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
        </div>
    );
}
