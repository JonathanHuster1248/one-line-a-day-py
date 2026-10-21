import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AttachmentViewer } from "./AttachmentViewer";
import { contentUrl } from "./attachments";
import { makeAttachment } from "../test/factories";

describe("AttachmentViewer", () => {
    const showModal = vi.fn(function (this: HTMLDialogElement) {
        this.setAttribute("open", "");
    });
    const close = vi.fn(function (this: HTMLDialogElement) {
        this.removeAttribute("open");
    });

    beforeEach(() => {
        // jsdom doesn't implement the modal dialog methods.
        HTMLDialogElement.prototype.showModal = showModal;
        HTMLDialogElement.prototype.close = close;
    });

    afterEach(() => {
        showModal.mockClear();
        close.mockClear();
    });

    it("opens as a modal named by the filename, showing the display image", () => {
        render(<AttachmentViewer attachment={makeAttachment()} onClose={vi.fn()} />);

        expect(showModal).toHaveBeenCalledTimes(1);
        const dialog = screen.getByRole("dialog", { name: "beach.jpg" });
        expect(dialog).toHaveAttribute("open");
        expect(screen.getByRole("img", { name: "beach.jpg" })).toHaveAttribute(
            "src",
            contentUrl("1", "att-1"),
        );
    });

    it("offers a download link to the attachment disposition", () => {
        render(<AttachmentViewer attachment={makeAttachment()} onClose={vi.fn()} />);

        const link = screen.getByRole("link", { name: "Download" });
        expect(link).toHaveAttribute("href", contentUrl("1", "att-1", true));
        expect(link).toHaveAttribute("download");
    });

    it("calls onClose from the Close button", async () => {
        const onClose = vi.fn();
        render(<AttachmentViewer attachment={makeAttachment()} onClose={onClose} />);

        await userEvent.setup().click(screen.getByRole("button", { name: "Close" }));

        expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("hands Esc to the parent instead of closing itself", () => {
        const onClose = vi.fn();
        render(<AttachmentViewer attachment={makeAttachment()} onClose={onClose} />);

        const notCancelled = fireEvent(
            screen.getByRole("dialog"),
            new Event("cancel", { bubbles: false, cancelable: true }),
        );

        expect(notCancelled).toBe(false);
        expect(onClose).toHaveBeenCalledTimes(1);
        expect(close).not.toHaveBeenCalled();
    });

    it("closes the dialog when unmounted", () => {
        const { unmount } = render(<AttachmentViewer attachment={makeAttachment()} onClose={vi.fn()} />);

        unmount();

        expect(close).toHaveBeenCalledTimes(1);
    });

    it("shows an error in place of the image when it fails, keeping Download and Close", () => {
        render(<AttachmentViewer attachment={makeAttachment()} onClose={vi.fn()} />);

        fireEvent.error(screen.getByRole("img"));

        expect(screen.getByText("This image couldn't be loaded.")).toBeInTheDocument();
        expect(screen.queryByRole("img")).not.toBeInTheDocument();
        expect(screen.getByRole("link", { name: "Download" })).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "Close" })).toBeInTheDocument();
    });
});
