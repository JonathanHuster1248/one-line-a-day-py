// Hand-kept in sync with the backend's AttachmentPublic (one_line_day_py/src/model.py).
export interface Attachment {
    id: string;
    entry_id: string;
    filename: string;
    kind: "image" | "pdf";
    content_type: string;
    has_thumbnail: boolean;
    width: number | null;
    height: number | null;
}

// Hand-kept in sync with the backend's JournalEntryPublic (one_line_day_py/src/schemas.py).
export interface Journal {
    id: string;
    author_id: string;
    date: string;
    message: string;
    attachments: Attachment[];
    // False only when the backend couldn't look up attachments for this entry.
    attachments_available: boolean;
}
