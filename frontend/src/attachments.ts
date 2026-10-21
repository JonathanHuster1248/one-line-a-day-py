import { API_BASE_URL } from "./config";
import type { Attachment } from "./models";

export type UploadStatus = "queued" | "uploading" | "done" | "failed";

export interface UploadResult {
    uploaded: Attachment[];
    failed: { file: File; error: string }[];
}

function attachmentsUrl(entryId: string): string {
    return `${API_BASE_URL}/journals/${entryId}/attachments`;
}

export function thumbnailUrl(entryId: string, attachmentId: string): string {
    return `${attachmentsUrl(entryId)}/${attachmentId}/thumbnail`;
}

export function contentUrl(entryId: string, attachmentId: string, download = false): string {
    const url = `${attachmentsUrl(entryId)}/${attachmentId}/content`;
    return download ? `${url}?download=true` : url;
}

// Messages for the statuses the backend maps its attachment errors to.
const UPLOAD_ERRORS: Record<number, string> = {
    400: "This entry already has the maximum number of attachments.",
    404: "The entry no longer exists.",
    413: "The file is too large.",
    415: "This file type isn't supported.",
    422: "The file couldn't be processed.",
    503: "Attachment storage is unavailable.",
};

export async function uploadAttachment(entryId: string, file: File): Promise<Attachment> {
    const body = new FormData();
    body.append("file", file);

    // No Content-Type header: the browser sets it, including the multipart boundary.
    // Unlike the journal endpoints, the file goes in the body rather than query params.
    const response = await fetch(`${attachmentsUrl(entryId)}/`, {
        method: "POST",
        credentials: "include",
        body,
    });

    if (!response.ok) {
        throw new Error(UPLOAD_ERRORS[response.status] ?? `Upload failed: ${response.status}`);
    }

    return (await response.json()) as Attachment;
}

/**
 * Uploads one file at a time, in order, and never throws: each failure is
 * recorded so the caller can report it and retry just those files.
 * `onStatus` reports each file moving from uploading to done or failed.
 */
export async function uploadAttachments(
    entryId: string,
    files: File[],
    onStatus?: (file: File, status: UploadStatus) => void,
): Promise<UploadResult> {
    const result: UploadResult = { uploaded: [], failed: [] };
    for (const file of files) {
        onStatus?.(file, "uploading");
        try {
            result.uploaded.push(await uploadAttachment(entryId, file));
            onStatus?.(file, "done");
        } catch (err) {
            result.failed.push({
                file,
                error: err instanceof Error ? err.message : "Upload failed.",
            });
            onStatus?.(file, "failed");
        }
    }
    return result;
}

export async function deleteAttachment(entryId: string, attachmentId: string): Promise<void> {
    const response = await fetch(`${attachmentsUrl(entryId)}/${attachmentId}`, {
        method: "DELETE",
        credentials: "include",
    });

    if (!response.ok) {
        throw new Error(`Failed to delete attachment: ${response.status}`);
    }
}
