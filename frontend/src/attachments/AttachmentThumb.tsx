import { useState } from "react";
import type { Attachment } from "../shared/models";
import { contentUrl, thumbnailUrl } from "./attachments";
import { FileIcon } from "../shared/FileIcon";

type LoadState = "loading" | "loaded" | "error";

/**
 * One fixed-size attachment tile. Images show a skeleton until the lazy
 * thumbnail loads and an in-place error with Retry if it fails; attachments
 * without a thumbnail (PDFs) show an icon and filename and open in a new tab.
 */
export function AttachmentThumb({
    attachment,
    onOpen,
}: {
    attachment: Attachment;
    onOpen: (attachment: Attachment) => void;
}) {
    const [loadState, setLoadState] = useState<LoadState>("loading");
    // Bumped on Retry to remount the <img>, which makes the browser request it again.
    const [attempt, setAttempt] = useState(0);

    if (!attachment.has_thumbnail) {
        return (
            <a
                className="attachment-thumb attachment-thumb-file"
                href={contentUrl(attachment.entry_id, attachment.id)}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={attachment.filename}
            >
                <FileIcon />
                <span className="attachment-thumb-name">{attachment.filename}</span>
            </a>
        );
    }

    if (loadState === "error") {
        return (
            <div className="attachment-thumb attachment-thumb-error">
                <FileIcon />
                <span className="attachment-thumb-name">{attachment.filename}</span>
                <button
                    type="button"
                    className="attachment-retry-button"
                    aria-label={`Retry loading ${attachment.filename}`}
                    onClick={() => {
                        setAttempt((n) => n + 1);
                        setLoadState("loading");
                    }}
                >
                    Retry
                </button>
            </div>
        );
    }

    const isLoading = loadState === "loading";
    // PDFs that gain a rendered thumbnail later still open in the browser's PDF viewer.
    const thumbnail = (
        <>
            {isLoading && <span className="attachment-skeleton" data-testid="attachment-skeleton" />}
            <img
                key={attempt}
                className={isLoading ? "attachment-thumb-img is-loading" : "attachment-thumb-img"}
                src={thumbnailUrl(attachment.entry_id, attachment.id)}
                alt={attachment.filename}
                loading="lazy"
                onLoad={() => setLoadState("loaded")}
                onError={() => setLoadState("error")}
            />
        </>
    );

    if (attachment.kind === "pdf") {
        return (
            <a
                className="attachment-thumb"
                href={contentUrl(attachment.entry_id, attachment.id)}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={attachment.filename}
            >
                {thumbnail}
            </a>
        );
    }

    return (
        <button
            type="button"
            className="attachment-thumb"
            aria-label={attachment.filename}
            onClick={() => onOpen(attachment)}
        >
            {thumbnail}
        </button>
    );
}
