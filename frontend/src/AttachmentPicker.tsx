import { useEffect, useId, useState } from "react";
import { MAX_ATTACHMENTS_PER_ENTRY, MAX_ATTACHMENT_BYTES } from "./config";
import { FileIcon } from "./FileIcon";
import type { UploadStatus } from "./attachments";

// A hint for the file browser only; the backend decides what it accepts.
const ACCEPT = "image/jpeg,image/png,image/webp,image/gif,image/heic,image/heif,.heic,.heif,application/pdf";
const MAX_MB = MAX_ATTACHMENT_BYTES / (1024 * 1024);

const STATUS_LABELS: Record<UploadStatus, string> = {
    queued: "Queued",
    uploading: "Uploading...",
    done: "Uploaded",
    failed: "Failed",
};

// Stable React keys per File object, so removing one file doesn't remount
// (and re-create previews for) the ones after it.
const fileKeys = new WeakMap<File, number>();
let nextFileKey = 0;
function keyFor(file: File): number {
    let key = fileKeys.get(file);
    if (key === undefined) {
        key = nextFileKey++;
        fileKeys.set(file, key);
    }
    return key;
}

function SelectedFile({
    file,
    status,
    disabled,
    onRemove,
}: {
    file: File;
    status: UploadStatus | undefined;
    disabled: boolean;
    onRemove: () => void;
}) {
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [previewFailed, setPreviewFailed] = useState(false);

    useEffect(() => {
        if (!file.type.startsWith("image/")) return;
        const url = URL.createObjectURL(file);
        setPreviewUrl(url);
        return () => URL.revokeObjectURL(url);
    }, [file]);

    return (
        <li className="picker-file">
            {previewUrl && !previewFailed ? (
                // Decorative: the filename next to it is the accessible text.
                <img className="picker-preview" src={previewUrl} alt="" onError={() => setPreviewFailed(true)} />
            ) : (
                <span className="picker-preview picker-preview-icon" data-testid="picker-file-icon">
                    <FileIcon />
                </span>
            )}
            <span className="picker-file-name">{file.name}</span>
            {status && <span className="picker-file-status">{STATUS_LABELS[status]}</span>}
            <button
                type="button"
                className="picker-remove-button"
                aria-label={`Remove ${file.name}`}
                onClick={onRemove}
                disabled={disabled}
            >
                ×
            </button>
        </li>
    );
}

/**
 * File selection for an entry: browse or drag and drop, with the count and size
 * limits checked up front. Controlled: the parent owns `files`. `existingCount`
 * is how many attachments the entry already has, so the cap counts both.
 */
export function AttachmentPicker({
    files,
    onChange,
    existingCount = 0,
    disabled = false,
    statuses,
}: {
    files: File[];
    onChange: (files: File[]) => void;
    existingCount?: number;
    disabled?: boolean;
    statuses?: Map<File, UploadStatus>;
}) {
    const inputId = useId();
    const [messages, setMessages] = useState<string[]>([]);
    const [isDragging, setIsDragging] = useState(false);

    const remaining = MAX_ATTACHMENTS_PER_ENTRY - existingCount - files.length;
    const atLimit = remaining <= 0;

    const addFiles = (incoming: File[]) => {
        if (disabled || incoming.length === 0) return;

        const errors: string[] = [];
        const accepted: File[] = [];
        let overLimit = false;
        for (const file of incoming) {
            if (file.size > MAX_ATTACHMENT_BYTES) {
                errors.push(`${file.name} is larger than ${MAX_MB} MB.`);
            } else if (accepted.length >= remaining) {
                overLimit = true;
            } else {
                accepted.push(file);
            }
        }
        if (overLimit) {
            errors.push(`An entry can have at most ${MAX_ATTACHMENTS_PER_ENTRY} attachments.`);
        }

        setMessages(errors);
        if (accepted.length > 0) onChange([...files, ...accepted]);
    };

    const removeFile = (index: number) => {
        setMessages([]);
        onChange(files.filter((_, i) => i !== index));
    };

    return (
        <div
            className={isDragging ? "attachment-picker is-dragging" : "attachment-picker"}
            data-testid="attachment-drop-zone"
            onDragOver={(e) => {
                e.preventDefault();
                if (!disabled) setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                addFiles(Array.from(e.dataTransfer.files));
            }}
        >
            <input
                id={inputId}
                className="visually-hidden"
                type="file"
                multiple
                accept={ACCEPT}
                disabled={disabled || atLimit}
                onChange={(e) => {
                    addFiles(Array.from(e.target.files ?? []));
                    // Clear so choosing the same file again still fires a change.
                    e.target.value = "";
                }}
            />
            <label htmlFor={inputId} className="picker-button">
                Attach files
            </label>
            <span className="picker-hint">
                {atLimit
                    ? `Attachment limit reached (${MAX_ATTACHMENTS_PER_ENTRY})`
                    : `or drop them here (up to ${MAX_ATTACHMENTS_PER_ENTRY}, ${MAX_MB} MB each)`}
            </span>
            {messages.length > 0 && (
                <ul className="picker-errors" role="alert">
                    {messages.map((message) => (
                        <li key={message}>{message}</li>
                    ))}
                </ul>
            )}
            {files.length > 0 && (
                <ul className="picker-files">
                    {files.map((file, i) => (
                        <SelectedFile
                            key={keyFor(file)}
                            file={file}
                            status={statuses?.get(file)}
                            disabled={disabled}
                            onRemove={() => removeFile(i)}
                        />
                    ))}
                </ul>
            )}
        </div>
    );
}
