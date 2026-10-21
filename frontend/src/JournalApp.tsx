import { useEffect, useState } from "react";
import { getJournals, createJournalEntry, updateJournalEntry, deleteJournalEntry, DuplicateDateError } from "./journals";
import { uploadAttachments, type UploadResult, type UploadStatus } from "./attachments";
import type { Attachment, Journal } from "./models";
import { useAuth } from "./AuthContext";
import { JournalBox } from "./JournalBox";
import { AttachmentPicker } from "./AttachmentPicker";
import { UploadFailureNotice } from "./UploadFailureNotice";
import { formatMonthDay, shiftDate, shiftYear, todayISODate } from "./date";

export function JournalApp() {
    const { logout } = useAuth();
    const [journals, setJournals] = useState<Journal[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [selectedDate, setSelectedDate] = useState<string>(todayISODate);
    const [message, setMessage] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [files, setFiles] = useState<File[]>([]);
    const [statuses, setStatuses] = useState<Map<File, UploadStatus>>(new Map());
    // Uploads that failed after their entry was created, kept so Retry can target that entry.
    const [uploadFailure, setUploadFailure] = useState<{ entryId: string; failed: UploadResult["failed"] } | null>(
        null,
    );
    const [isRetrying, setIsRetrying] = useState(false);

    useEffect(() => {
        let isCurrent = true;

        async function loadJournals() {
            setIsLoading(true);
            setError(null);
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
        setUploadFailure(null);
        let created: Journal;
        try {
            created = await createJournalEntry(selectedDate, message);
        } catch (error) {
            console.error("Failed to create journal entry:", error);
            setError(error instanceof DuplicateDateError ? error.message : "Failed to save entry. Please try again.");
            setIsSubmitting(false);
            return;
        }

        // The entry is saved before any file is sent, so a failed upload never loses it.
        setJournals((prev) => [...prev, created]);
        setMessage("");

        if (files.length > 0) {
            setStatuses(new Map(files.map((file) => [file, "queued"])));
            const result = await uploadAttachments(created.id, files, (file, status) =>
                setStatuses((prev) => new Map(prev).set(file, status)),
            );
            addAttachments(created.id, result.uploaded);
            if (result.failed.length > 0) {
                setUploadFailure({ entryId: created.id, failed: result.failed });
            }
            setFiles([]);
            setStatuses(new Map());
        }
        setIsSubmitting(false);
    };

    const addAttachments = (entryId: string, attachments: Attachment[]) => {
        if (attachments.length === 0) return;
        setJournals((prev) =>
            prev.map((j) => (j.id === entryId ? { ...j, attachments: [...j.attachments, ...attachments] } : j)),
        );
    };

    const handleRetryUploads = async () => {
        if (!uploadFailure) return;
        setIsRetrying(true);
        const result = await uploadAttachments(
            uploadFailure.entryId,
            uploadFailure.failed.map((f) => f.file),
        );
        addAttachments(uploadFailure.entryId, result.uploaded);
        setUploadFailure(result.failed.length > 0 ? { entryId: uploadFailure.entryId, failed: result.failed } : null);
        setIsRetrying(false);
    };

    const handleAttachmentsChange = (journalId: string, attachments: Attachment[]) => {
        setJournals((prev) => prev.map((j) => (j.id === journalId ? { ...j, attachments } : j)));
    };

    const handleUpdate = async (journal: Journal, date: string, message: string) => {
        const updated = await updateJournalEntry(journal.id, date, message);
        // An entry moved to another month/day no longer belongs on this page.
        const stillHere = updated.date.slice(5) === selectedDate.slice(5);
        setJournals((prev) =>
            stillHere ? prev.map((j) => (j.id === updated.id ? updated : j)) : prev.filter((j) => j.id !== updated.id),
        );
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
                            onAttachmentsChange={handleAttachmentsChange}
                        />
                    ))}
                </div>
                <form onSubmit={handleSubmit} className="new-entry-form">
                    <div className="new-entry-row">
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
                    </div>
                    <AttachmentPicker files={files} onChange={setFiles} disabled={isSubmitting} statuses={statuses} />
                </form>
                {uploadFailure && (
                    <UploadFailureNotice
                        failed={uploadFailure.failed}
                        onRetry={handleRetryUploads}
                        onDismiss={() => setUploadFailure(null)}
                        retrying={isRetrying}
                    />
                )}
            </div>
        </div>
    );
}
