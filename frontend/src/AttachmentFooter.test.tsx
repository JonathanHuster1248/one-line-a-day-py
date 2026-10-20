import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AttachmentFooter } from "./AttachmentFooter";
import { AttachmentThumb } from "./AttachmentThumb";
import type { Attachment } from "./models";

vi.mock("./AttachmentThumb", async (importOriginal) => {
    const actual = await importOriginal<typeof import("./AttachmentThumb")>();
    return { AttachmentThumb: vi.fn(actual.AttachmentThumb) };
});

const mockedThumb = vi.mocked(AttachmentThumb);

function makeAttachment(overrides: Partial<Attachment> = {}): Attachment {
    return {
        id: "att-1",
        entry_id: "entry-1",
        filename: "beach.jpg",
        kind: "image",
        content_type: "image/webp",
        has_thumbnail: true,
        width: 2048,
        height: 1536,
        ...overrides,
    };
}

describe("AttachmentFooter", () => {
    beforeEach(() => {
        // jsdom doesn't implement the modal dialog methods.
        HTMLDialogElement.prototype.showModal = vi.fn(function (this: HTMLDialogElement) {
            this.setAttribute("open", "");
        });
        HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) {
            this.removeAttribute("open");
        });
    });

    afterEach(() => {
        mockedThumb.mockClear();
        vi.restoreAllMocks();
    });

    it("renders nothing when the entry has no attachments", () => {
        const { container } = render(<AttachmentFooter attachments={[]} available={true} />);
        expect(container).toBeEmptyDOMElement();
    });

    it("renders a thumbnail for every attachment", () => {
        render(
            <AttachmentFooter
                attachments={[
                    makeAttachment(),
                    makeAttachment({ id: "att-2", filename: "dog.png" }),
                    makeAttachment({
                        id: "att-3",
                        filename: "ticket.pdf",
                        kind: "pdf",
                        content_type: "application/pdf",
                        has_thumbnail: false,
                    }),
                ]}
                available={true}
            />,
        );

        expect(screen.getByRole("button", { name: "beach.jpg" })).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "dog.png" })).toBeInTheDocument();
        expect(screen.getByRole("link", { name: "ticket.pdf" })).toBeInTheDocument();
    });

    it("shows the unavailable note when the backend couldn't look up attachments", () => {
        render(<AttachmentFooter attachments={[]} available={false} />);
        expect(screen.getByText("Attachments unavailable")).toBeInTheDocument();
    });

    it("opens the viewer with the display image and a download link, and closes it", async () => {
        const user = userEvent.setup();
        render(<AttachmentFooter attachments={[makeAttachment()]} available={true} />);

        await user.click(screen.getByRole("button", { name: "beach.jpg" }));

        const dialog = screen.getByRole("dialog", { name: "beach.jpg" });
        expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled();
        const image = screen.getAllByRole("img", { name: "beach.jpg" }).find((el) => dialog.contains(el));
        expect(image?.getAttribute("src")).toMatch(/\/attachments\/att-1\/content$/);
        expect(screen.getByRole("link", { name: "Download" }).getAttribute("href")).toMatch(
            /\/attachments\/att-1\/content\?download=true$/,
        );

        await user.click(screen.getByRole("button", { name: "Close" }));

        expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
        expect(HTMLDialogElement.prototype.close).toHaveBeenCalled();
    });

    it("closes the viewer on Esc", async () => {
        const user = userEvent.setup();
        render(<AttachmentFooter attachments={[makeAttachment()]} available={true} />);

        await user.click(screen.getByRole("button", { name: "beach.jpg" }));
        // The platform turns Esc on a modal dialog into a cancel event.
        fireEvent(screen.getByRole("dialog"), new Event("cancel", { cancelable: true }));

        expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("shows an error inside the viewer when the image fails, and can still close", async () => {
        const user = userEvent.setup();
        render(<AttachmentFooter attachments={[makeAttachment()]} available={true} />);

        await user.click(screen.getByRole("button", { name: "beach.jpg" }));
        const dialog = screen.getByRole("dialog");
        const image = screen.getAllByRole("img", { name: "beach.jpg" }).find((el) => dialog.contains(el))!;
        fireEvent.error(image);

        expect(screen.getByText("This image couldn't be loaded.")).toBeInTheDocument();
        expect(screen.getByRole("link", { name: "Download" })).toBeInTheDocument();

        await user.click(screen.getByRole("button", { name: "Close" }));
        expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("contains a render error to the footer", () => {
        vi.spyOn(console, "error").mockImplementation(() => {});
        mockedThumb.mockImplementation(() => {
            throw new Error("boom");
        });

        render(
            <div>
                <p>Entry text</p>
                <AttachmentFooter attachments={[makeAttachment()]} available={true} />
            </div>,
        );

        expect(screen.getByText("Attachments unavailable")).toBeInTheDocument();
        expect(screen.getByText("Entry text")).toBeInTheDocument();
    });
});
