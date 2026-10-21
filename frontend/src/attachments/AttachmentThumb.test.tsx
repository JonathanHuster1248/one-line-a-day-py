import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AttachmentThumb } from "./AttachmentThumb";
import { makeAttachment } from "../test/factories";

describe("AttachmentThumb", () => {
    it("shows a skeleton until the lazy thumbnail loads", () => {
        render(<AttachmentThumb attachment={makeAttachment()} onOpen={vi.fn()} />);

        const img = screen.getByRole("img", { name: "beach.jpg" });
        expect(img).toHaveAttribute("loading", "lazy");
        expect(img.getAttribute("src")).toMatch(/\/journals\/1\/attachments\/att-1\/thumbnail$/);
        expect(screen.getByTestId("attachment-skeleton")).toBeInTheDocument();
        expect(img).toHaveClass("is-loading");
    });

    it("swaps in the image once it loads", () => {
        render(<AttachmentThumb attachment={makeAttachment()} onOpen={vi.fn()} />);

        const img = screen.getByRole("img", { name: "beach.jpg" });
        fireEvent.load(img);

        expect(screen.queryByTestId("attachment-skeleton")).not.toBeInTheDocument();
        expect(img).not.toHaveClass("is-loading");
    });

    it("shows an error state with Retry when the thumbnail fails, and Retry re-requests it", async () => {
        const user = userEvent.setup();
        render(<AttachmentThumb attachment={makeAttachment()} onOpen={vi.fn()} />);

        fireEvent.error(screen.getByRole("img", { name: "beach.jpg" }));

        expect(screen.queryByRole("img")).not.toBeInTheDocument();
        expect(screen.getByText("beach.jpg")).toBeInTheDocument();

        await user.click(screen.getByRole("button", { name: "Retry loading beach.jpg" }));

        const retried = screen.getByRole("img", { name: "beach.jpg" });
        expect(screen.getByTestId("attachment-skeleton")).toBeInTheDocument();
        fireEvent.load(retried);
        expect(screen.queryByRole("button", { name: /Retry/ })).not.toBeInTheDocument();
    });

    it("renders an image thumbnail as a button named by the filename that opens the viewer", async () => {
        const onOpen = vi.fn();
        const attachment = makeAttachment();
        const user = userEvent.setup();
        render(<AttachmentThumb attachment={attachment} onOpen={onOpen} />);

        await user.click(screen.getByRole("button", { name: "beach.jpg" }));

        expect(onOpen).toHaveBeenCalledWith(attachment);
    });

    it("opens from the keyboard", async () => {
        const onOpen = vi.fn();
        const user = userEvent.setup();
        render(<AttachmentThumb attachment={makeAttachment()} onOpen={onOpen} />);

        await user.tab();
        expect(screen.getByRole("button", { name: "beach.jpg" })).toHaveFocus();
        await user.keyboard("{Enter}");

        expect(onOpen).toHaveBeenCalledTimes(1);
    });

    it("renders a PDF without a thumbnail as an icon and filename linking to a new tab", () => {
        render(
            <AttachmentThumb
                attachment={makeAttachment({
                    filename: "ticket.pdf",
                    kind: "pdf",
                    content_type: "application/pdf",
                    has_thumbnail: false,
                    width: null,
                    height: null,
                })}
                onOpen={vi.fn()}
            />,
        );

        const link = screen.getByRole("link", { name: "ticket.pdf" });
        expect(link.getAttribute("href")).toMatch(/\/journals\/1\/attachments\/att-1\/content$/);
        expect(link).toHaveAttribute("target", "_blank");
        expect(link).toHaveAttribute("rel", "noopener noreferrer");
        expect(link).toHaveClass("attachment-thumb");
        expect(screen.getByText("ticket.pdf")).toBeInTheDocument();
        expect(screen.queryByRole("img")).not.toBeInTheDocument();
    });
});
