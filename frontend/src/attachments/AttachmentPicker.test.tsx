import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { AttachmentPicker } from "./AttachmentPicker";
import type { UploadStatus } from "./attachments";
import { MAX_ATTACHMENT_BYTES } from "../shared/config";
import { makeFile } from "../test/factories";

// The picker is controlled; this owns the files like JournalApp/JournalBox will.
function Harness({
    initial = [],
    existingCount,
    disabled,
    statuses,
    onChange,
}: {
    initial?: File[];
    existingCount?: number;
    disabled?: boolean;
    statuses?: Map<File, UploadStatus>;
    onChange?: (files: File[]) => void;
}) {
    const [files, setFiles] = useState<File[]>(initial);
    return (
        <AttachmentPicker
            files={files}
            onChange={(next) => {
                setFiles(next);
                onChange?.(next);
            }}
            existingCount={existingCount}
            disabled={disabled}
            statuses={statuses}
        />
    );
}

describe("AttachmentPicker", () => {
    let objectUrlCount = 0;

    beforeEach(() => {
        objectUrlCount = 0;
        // jsdom doesn't implement object URLs.
        URL.createObjectURL = vi.fn(() => `blob:preview-${++objectUrlCount}`);
        URL.revokeObjectURL = vi.fn();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("adds files chosen with the file browser", async () => {
        const onChange = vi.fn();
        const user = userEvent.setup();
        render(<Harness onChange={onChange} />);

        const a = makeFile("beach.jpg");
        const b = makeFile("ticket.pdf", "application/pdf");
        await user.upload(screen.getByLabelText("Attach files"), [a, b]);

        expect(onChange).toHaveBeenLastCalledWith([a, b]);
        expect(screen.getByText("beach.jpg")).toBeInTheDocument();
        expect(screen.getByText("ticket.pdf")).toBeInTheDocument();
    });

    it("adds files dropped on the drop zone", () => {
        const onChange = vi.fn();
        render(<Harness onChange={onChange} />);

        const file = makeFile("dropped.png", "image/png");
        fireEvent.drop(screen.getByTestId("attachment-drop-zone"), { dataTransfer: { files: [file] } });

        expect(onChange).toHaveBeenLastCalledWith([file]);
        expect(screen.getByText("dropped.png")).toBeInTheDocument();
    });

    it("ignores drops while disabled", () => {
        const onChange = vi.fn();
        render(<Harness onChange={onChange} disabled />);

        fireEvent.drop(screen.getByTestId("attachment-drop-zone"), {
            dataTransfer: { files: [makeFile("dropped.png")] },
        });

        expect(onChange).not.toHaveBeenCalled();
        expect(screen.getByLabelText("Attach files")).toBeDisabled();
    });

    it("rejects files over the size limit with a message and keeps the rest", async () => {
        const onChange = vi.fn();
        const user = userEvent.setup();
        render(<Harness onChange={onChange} />);

        const ok = makeFile("ok.jpg");
        const big = makeFile("huge.jpg", "image/jpeg", MAX_ATTACHMENT_BYTES + 1);
        await user.upload(screen.getByLabelText("Attach files"), [ok, big]);

        expect(onChange).toHaveBeenLastCalledWith([ok]);
        expect(screen.getByRole("alert")).toHaveTextContent("huge.jpg is larger than 15 MB.");
        expect(screen.queryByText("huge.jpg")).not.toBeInTheDocument();
    });

    it("accepts a file exactly at the size limit", async () => {
        const onChange = vi.fn();
        const user = userEvent.setup();
        render(<Harness onChange={onChange} />);

        const edge = makeFile("edge.jpg", "image/jpeg", MAX_ATTACHMENT_BYTES);
        await user.upload(screen.getByLabelText("Attach files"), [edge]);

        expect(onChange).toHaveBeenLastCalledWith([edge]);
        expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    it("rejects files beyond the count limit, counting existing attachments", async () => {
        const onChange = vi.fn();
        const user = userEvent.setup();
        render(<Harness existingCount={3} onChange={onChange} />);

        const files = [makeFile("1.jpg"), makeFile("2.jpg"), makeFile("3.jpg")];
        await user.upload(screen.getByLabelText("Attach files"), files);

        expect(onChange).toHaveBeenLastCalledWith(files.slice(0, 2));
        expect(screen.getByRole("alert")).toHaveTextContent("An entry can have at most 5 attachments.");
        expect(screen.queryByText("3.jpg")).not.toBeInTheDocument();
        // At the cap, the input is disabled so no more can be picked.
        expect(screen.getByLabelText("Attach files")).toBeDisabled();
        expect(screen.getByText("Attachment limit reached (5)")).toBeInTheDocument();
    });

    it("removes a selected file and revokes its preview URL", async () => {
        const a = makeFile("a.jpg");
        const b = makeFile("b.jpg");
        const onChange = vi.fn();
        const user = userEvent.setup();
        render(<Harness initial={[a, b]} onChange={onChange} />);

        await user.click(screen.getByRole("button", { name: "Remove a.jpg" }));

        expect(onChange).toHaveBeenLastCalledWith([b]);
        expect(screen.queryByText("a.jpg")).not.toBeInTheDocument();
        expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:preview-1");
        expect(URL.revokeObjectURL).not.toHaveBeenCalledWith("blob:preview-2");
    });

    it("revokes preview URLs on unmount", () => {
        const { unmount } = render(<Harness initial={[makeFile("a.jpg"), makeFile("b.jpg")]} />);

        unmount();

        expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:preview-1");
        expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:preview-2");
    });

    it("previews images and falls back to an icon when a preview can't render", () => {
        const { container } = render(<Harness initial={[makeFile("photo.heic", "image/heic")]} />);

        const preview = container.querySelector("img.picker-preview")!;
        expect(preview).toHaveAttribute("src", "blob:preview-1");
        expect(screen.queryByTestId("picker-file-icon")).not.toBeInTheDocument();

        fireEvent.error(preview);

        expect(container.querySelector("img.picker-preview")).not.toBeInTheDocument();
        expect(screen.getByTestId("picker-file-icon")).toBeInTheDocument();
    });

    it("shows an icon without creating a preview for non-images", () => {
        render(<Harness initial={[makeFile("ticket.pdf", "application/pdf")]} />);

        expect(screen.getByTestId("picker-file-icon")).toBeInTheDocument();
        expect(URL.createObjectURL).not.toHaveBeenCalled();
    });

    it("shows per-file upload status", () => {
        const a = makeFile("a.jpg");
        const b = makeFile("b.jpg");
        render(
            <Harness
                initial={[a, b]}
                statuses={
                    new Map<File, UploadStatus>([
                        [a, "done"],
                        [b, "failed"],
                    ])
                }
            />,
        );

        expect(screen.getByText("Uploaded")).toBeInTheDocument();
        expect(screen.getByText("Failed")).toBeInTheDocument();
    });

    it("disables removal while disabled", () => {
        render(<Harness initial={[makeFile("a.jpg")]} disabled />);
        expect(screen.getByRole("button", { name: "Remove a.jpg" })).toBeDisabled();
    });

    it("is operable by keyboard", async () => {
        const onChange = vi.fn();
        const user = userEvent.setup();
        render(<Harness onChange={onChange} />);

        // The visually hidden input is the first tab stop.
        await user.tab();
        const input = screen.getByLabelText("Attach files");
        expect(input).toHaveFocus();

        const file = makeFile("a.jpg");
        await user.upload(input, file);

        // Tab on to the remove button and press it.
        await user.tab();
        expect(screen.getByRole("button", { name: "Remove a.jpg" })).toHaveFocus();
        await user.keyboard("{Enter}");

        expect(onChange).toHaveBeenLastCalledWith([]);
    });
});
