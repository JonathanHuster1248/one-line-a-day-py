import { useState } from "react";
import type { Journal } from "./models";
import { formatYear } from "./date";

export function JournalBox({
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
    const [error, setError] = useState<string | null>(null);

    const startEditing = () => {
        setEditDate(journal.date);
        setEditMessage(journal.message);
        setError(null);
        setIsEditing(true);
    };

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editMessage.trim()) return;

        setIsSaving(true);
        setError(null);
        try {
            await onUpdate(journal, editDate, editMessage);
            setIsEditing(false);
        } catch (error) {
            console.error("Failed to update journal entry:", error);
            setError("Failed to save changes. Please try again.");
        } finally {
            setIsSaving(false);
        }
    };

    const handleDelete = async () => {
        if (!window.confirm("Delete this journal entry?")) return;

        setIsDeleting(true);
        setError(null);
        try {
            await onDelete(journal);
        } catch (error) {
            console.error("Failed to delete journal entry:", error);
            setError("Failed to delete entry. Please try again.");
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
                {error && <p className="box-error">{error}</p>}
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
            {error && <p className="box-error">{error}</p>}
        </div>
    );
}
