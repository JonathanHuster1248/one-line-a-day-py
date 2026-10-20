import { useState } from "react";
import type { Attachment, Journal } from "./models";
import { formatYear } from "./date";
import { deleteAttachment, uploadAttachments, type UploadResult, type UploadStatus } from "./attachments";
import { AttachmentFooter } from "./AttachmentFooter";
import { AttachmentPicker } from "./AttachmentPicker";
import { UploadFailureNotice } from "./UploadFailureNotice";
import { FileIcon } from "./FileIcon";

export function JournalBox({
    journal,
    onUpdate,
    onDelete,
    onAttachmentsChange,
}: {
    journal: Journal;
    onUpdate: (journal: Journal, date: string, message: string) => Promise<void>;
    onDelete: (journal: Journal) => Promise<void>;
    onAttachmentsChange: (journalId: string, attachments: Attachment[]) => void;
}) {
    const [isEditing, setIsEditing] = useState(false);
    const [editDate, setEditDate] = useState(journal.date);
    const [editMessage, setEditMessage] = useState(journal.message);
    const [removedIds, setRemovedIds] = useState<Set<string>>(new Set());
    const [newFiles, setNewFiles] = useState<File[]>([]);
    const [statuses, setStatuses] = useState<Map<File, UploadStatus>>(new Map());
    const [isSaving, setIsSaving] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [uploadFailed, setUploadFailed] = useState<UploadResult["failed"]>([]);
    const [isRetrying, setIsRetrying] = useState(false);

    const keptAttachments = journal.attachments.filter((a) => !removedIds.has(a.id));

    const startEditing = () => {
        setEditDate(journal.date);
        setEditMessage(journal.message);
        setRemovedIds(new Set());
        setNewFiles([]);
        setStatuses(new Map());
        setError(null);
        setIsEditing(true);
    };

    // Deletes removed attachments and uploads added ones after the text has saved.
    // Failures here are reported but never undo the text save.
    const saveAttachments = async () => {
        const failedDeletes: Attachment[] = [];
        for (const attachment of journal.attachments.filter((a) => removedIds.has(a.id))) {
            try {
                await deleteAttachment(journal.id, attachment.id);
            } catch (error) {
                console.error("Failed to delete attachment:", error);
                failedDeletes.push(attachment);
            }
        }

        let result: UploadResult = { uploaded: [], failed: [] };
        if (newFiles.length > 0) {
            setStatuses(new Map(newFiles.map((file) => [file, "queued"])));
            result = await uploadAttachments(journal.id, newFiles, (file, status) =>
                setStatuses((prev) => new Map(prev).set(file, status)),
            );
        }

        if (removedIds.size > 0 || result.uploaded.length > 0) {
            const failedIds = new Set(failedDeletes.map((a) => a.id));
            onAttachmentsChange(journal.id, [
                ...journal.attachments.filter((a) => !removedIds.has(a.id) || failedIds.has(a.id)),
                ...result.uploaded,
            ]);
        }
        if (failedDeletes.length > 0) {
            setError(`Couldn't remove ${failedDeletes.map((a) => a.filename).join(", ")}. Please try again.`);
        }
        setUploadFailed(result.failed);
    };

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editMessage.trim()) return;

        setIsSaving(true);
        setError(null);
        setUploadFailed([]);
        try {
            await onUpdate(journal, editDate, editMessage);
        } catch (error) {
            console.error("Failed to update journal entry:", error);
            setError("Failed to save changes. Please try again.");
            setIsSaving(false);
            return;
        }

        await saveAttachments();
        setIsSaving(false);
        setIsEditing(false);
    };

    const handleRetryUploads = async () => {
        setIsRetrying(true);
        const result = await uploadAttachments(
            journal.id,
            uploadFailed.map((f) => f.file),
        );
        if (result.uploaded.length > 0) {
            onAttachmentsChange(journal.id, [...journal.attachments, ...result.uploaded]);
        }
        setUploadFailed(result.failed);
        setIsRetrying(false);
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
                {keptAttachments.length > 0 && (
                    <ul className="picker-files edit-attachments">
                        {keptAttachments.map((attachment) => (
                            <li key={attachment.id} className="picker-file">
                                <span className="picker-preview picker-preview-icon">
                                    <FileIcon />
                                </span>
                                <span className="picker-file-name">{attachment.filename}</span>
                                <button
                                    type="button"
                                    className="picker-remove-button"
                                    aria-label={`Remove ${attachment.filename}`}
                                    onClick={() => setRemovedIds((prev) => new Set(prev).add(attachment.id))}
                                    disabled={isSaving}
                                >
                                    ×
                                </button>
                            </li>
                        ))}
                    </ul>
                )}
                <AttachmentPicker
                    files={newFiles}
                    onChange={setNewFiles}
                    existingCount={keptAttachments.length}
                    disabled={isSaving}
                    statuses={statuses}
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
            <AttachmentFooter attachments={journal.attachments} available={journal.attachments_available} />
            {error && <p className="box-error">{error}</p>}
            <UploadFailureNotice
                failed={uploadFailed}
                onRetry={handleRetryUploads}
                onDismiss={() => setUploadFailed([])}
                retrying={isRetrying}
            />
        </div>
    );
}
