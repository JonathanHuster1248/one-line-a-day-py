import { Component, useState, type ReactNode } from "react";
import type { Attachment } from "./models";
import { AttachmentThumb } from "./AttachmentThumb";
import { AttachmentViewer } from "./AttachmentViewer";

function UnavailableNote() {
    return <p className="attachments-unavailable">Attachments unavailable</p>;
}

/**
 * Contains any render error in the attachments area so the rest of the entry
 * (text, Edit, Delete) keeps working.
 */
class AttachmentErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
    state = { hasError: false };

    static getDerivedStateFromError() {
        return { hasError: true };
    }

    componentDidCatch(error: unknown) {
        console.error("Attachments failed to render:", error);
    }

    render() {
        return this.state.hasError ? <UnavailableNote /> : this.props.children;
    }
}

function AttachmentList({ attachments }: { attachments: Attachment[] }) {
    const [viewing, setViewing] = useState<Attachment | null>(null);

    return (
        <div className="attachment-footer">
            {attachments.map((attachment) => (
                <AttachmentThumb key={attachment.id} attachment={attachment} onOpen={setViewing} />
            ))}
            {viewing && <AttachmentViewer attachment={viewing} onClose={() => setViewing(null)} />}
        </div>
    );
}

export function AttachmentFooter({ attachments, available }: { attachments: Attachment[]; available: boolean }) {
    if (!available) return <UnavailableNote />;
    if (attachments.length === 0) return null;

    return (
        <AttachmentErrorBoundary>
            <AttachmentList attachments={attachments} />
        </AttachmentErrorBoundary>
    );
}
