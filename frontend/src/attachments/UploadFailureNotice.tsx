import type { UploadResult } from "./attachments";

/** Lists files that failed to upload, with Retry and Dismiss. Shared by create and edit. */
export function UploadFailureNotice({
    failed,
    onRetry,
    onDismiss,
    retrying = false,
}: {
    failed: UploadResult["failed"];
    onRetry: () => void;
    onDismiss: () => void;
    retrying?: boolean;
}) {
    if (failed.length === 0) return null;

    return (
        <div className="upload-failure-notice" role="alert">
            <p>
                {failed.length === 1 ? "1 file" : `${failed.length} files`} couldn't be uploaded. Your entry was
                saved.
            </p>
            <ul>
                {failed.map(({ file, error }, i) => (
                    <li key={`${i}-${file.name}`}>
                        <span className="upload-failure-name">{file.name}</span>: {error}
                    </li>
                ))}
            </ul>
            <div className="box-actions">
                <button type="button" className="save-button" onClick={onRetry} disabled={retrying}>
                    {retrying ? "Retrying..." : "Retry"}
                </button>
                <button type="button" className="cancel-button" onClick={onDismiss} disabled={retrying}>
                    Dismiss
                </button>
            </div>
        </div>
    );
}
