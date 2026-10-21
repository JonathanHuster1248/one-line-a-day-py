import { useEffect, useRef, useState } from "react";
import type { Attachment } from "../shared/models";
import { contentUrl } from "./attachments";

/**
 * Modal viewer for one image attachment, shown with the native <dialog> so
 * Esc and focus handling come from the platform. The parent mounts it to open
 * and unmounts it (via onClose) to close.
 */
export function AttachmentViewer({ attachment, onClose }: { attachment: Attachment; onClose: () => void }) {
    const dialogRef = useRef<HTMLDialogElement>(null);
    const [failed, setFailed] = useState(false);

    useEffect(() => {
        const dialog = dialogRef.current;
        if (!dialog) return;
        dialog.showModal();
        // Closing (rather than just removing) the dialog returns focus to the thumbnail.
        return () => {
            if (dialog.open) dialog.close();
        };
    }, []);

    return (
        <dialog
            ref={dialogRef}
            className="attachment-viewer"
            aria-label={attachment.filename}
            onCancel={(e) => {
                // Esc: let the parent unmount us instead of the dialog closing itself.
                e.preventDefault();
                onClose();
            }}
        >
            {failed ? (
                <p className="attachment-viewer-error">This image couldn't be loaded.</p>
            ) : (
                <img
                    className="attachment-viewer-img"
                    src={contentUrl(attachment.entry_id, attachment.id)}
                    alt={attachment.filename}
                    onError={() => setFailed(true)}
                />
            )}
            <div className="attachment-viewer-actions">
                <a className="save-button" href={contentUrl(attachment.entry_id, attachment.id, true)} download>
                    Download
                </a>
                <button type="button" className="cancel-button" onClick={onClose}>
                    Close
                </button>
            </div>
        </dialog>
    );
}
