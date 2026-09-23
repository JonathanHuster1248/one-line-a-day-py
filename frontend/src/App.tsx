import { useEffect, useState } from "react";
import { getJournals, createJournalEntry, updateJournalEntry, deleteJournalEntry } from "./greeting";
import { useAuth } from "./AuthContext";
import { AuthForms } from "./AuthForms";

export default function App() {
    const { user, loading } = useAuth();

    if (loading) {
        return <div>Loading...</div>;
    }

    if (!user) {
        return <AuthForms />;
    }

    return <JournalApp />;
}

function JournalApp() {
    const { logout } = useAuth();
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

    const handleUpdate = async (journal: Journal, date: string, message: string) => {
        const updated = await updateJournalEntry(journal.id, date, message);
        setJournals((prev) =>
            prev ? prev.map((j) => (j.id === updated.id ? updated : j)) : prev
        );
    };

    const handleDelete = async (journal: Journal) => {
        await deleteJournalEntry(journal.id);
        setJournals((prev) => (prev ? prev.filter((j) => j.id !== journal.id) : prev));
    };

    if (journals === null) {
        return <div>Awaiting Entry</div>;
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

function formatMonthDay(dateStr: string): string {
    const [year, month, day] = dateStr.split('-').map(Number);
    const monthName = new Date(year, month - 1, day).toLocaleString('en-US', { month: 'long' });
    return `${monthName.toUpperCase()} ${day}`;
}

function shiftDate(dateStr: string, deltaDays: number): string {
    const [year, month, day] = dateStr.split('-').map(Number);
    const date = new Date(year, month - 1, day);
    date.setDate(date.getDate() + deltaDays);

    const newYear = date.getFullYear();
    const newMonth = String(date.getMonth() + 1).padStart(2, '0');
    const newDay = String(date.getDate()).padStart(2, '0');
    return `${newYear}-${newMonth}-${newDay}`;
}

function shiftYear(dateStr: string, deltaYears: number): string {
    const [year, month, day] = dateStr.split('-').map(Number);
    const date = new Date(year, month - 1, day);
    date.setFullYear(date.getFullYear() + deltaYears);

    const newYear = date.getFullYear();
    const newMonth = String(date.getMonth() + 1).padStart(2, '0');
    const newDay = String(date.getDate()).padStart(2, '0');
    return `${newYear}-${newMonth}-${newDay}`;
}

function formatYear(dateStr: string): string {
    return dateStr.split('-')[0];
}

function JournalBox({
    journal,
    onUpdate,
    onDelete,
}: {
    journal: Journal;
    onUpdate: (journal: Journal, date: string, message: string) => Promise<void>;
    onDelete: (journal: Journal) => Promise<void>;
}) {
    const [isEditing, setIsEditing] = useState(false);
    const [editDate, setEditDate] = useState(journal.date);
    const [editMessage, setEditMessage] = useState(journal.message);
    const [isSaving, setIsSaving] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);

    const startEditing = () => {
        setEditDate(journal.date);
        setEditMessage(journal.message);
        setIsEditing(true);
    };

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editMessage.trim()) return;

        setIsSaving(true);
        try {
            await onUpdate(journal, editDate, editMessage);
            setIsEditing(false);
        } catch (error) {
            console.error("Failed to update journal entry:", error);
        } finally {
            setIsSaving(false);
        }
    };

    const handleDelete = async () => {
        if (!window.confirm("Delete this journal entry?")) return;

        setIsDeleting(true);
        try {
            await onDelete(journal);
        } catch (error) {
            console.error("Failed to delete journal entry:", error);
            setIsDeleting(false);
        }
    };

    if (isEditing) {
        return (
            <form className="box" onSubmit={handleSave}>
                <input
                    type="date"
                    value={editDate}
                    onChange={(e) => setEditDate(e.target.value)}
                    disabled={isSaving}
                />
                <input
                    type="text"
                    value={editMessage}
                    onChange={(e) => setEditMessage(e.target.value)}
                    disabled={isSaving}
                />
                <div className="box-actions">
                    <button type="submit" className="save-button" disabled={isSaving || !editMessage.trim()}>
                        {isSaving ? "Saving..." : "Save"}
                    </button>
                    <button
                        type="button"
                        className="cancel-button"
                        onClick={() => setIsEditing(false)}
                        disabled={isSaving}
                    >
                        Cancel
                    </button>
                </div>
            </form>
        );
    }

    return (
        <div className="box">
            <div className="box-actions-view">
                <button type="button" className="edit-button" onClick={startEditing}>
                    Edit
                </button>
                <button type="button" className="delete-button" onClick={handleDelete} disabled={isDeleting}>
                    {isDeleting ? "Deleting..." : "Delete"}
                </button>
            </div>
            <h2>{formatYear(journal.date)}</h2>
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


