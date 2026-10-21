import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { UploadFailureNotice } from "./UploadFailureNotice";

const failed = [
    { file: new File(["a"], "beach.jpg", { type: "image/jpeg" }), error: "The file is too large." },
    { file: new File(["b"], "notes.txt", { type: "text/plain" }), error: "This file type isn't supported." },
];

describe("UploadFailureNotice", () => {
    it("lists each failed filename with its error", () => {
        render(<UploadFailureNotice failed={failed} onRetry={vi.fn()} onDismiss={vi.fn()} />);

        expect(screen.getByRole("alert")).toHaveTextContent("2 files couldn't be uploaded");
        expect(screen.getByText("beach.jpg")).toBeInTheDocument();
        expect(screen.getByText("notes.txt")).toBeInTheDocument();
        expect(screen.getByText(/The file is too large\./)).toBeInTheDocument();
        expect(screen.getByText(/This file type isn't supported\./)).toBeInTheDocument();
    });

    it("renders nothing when nothing failed", () => {
        const { container } = render(<UploadFailureNotice failed={[]} onRetry={vi.fn()} onDismiss={vi.fn()} />);
        expect(container).toBeEmptyDOMElement();
    });

    it("calls onRetry when Retry is clicked", async () => {
        const onRetry = vi.fn();
        const user = userEvent.setup();
        render(<UploadFailureNotice failed={failed} onRetry={onRetry} onDismiss={vi.fn()} />);

        await user.click(screen.getByRole("button", { name: "Retry" }));

        expect(onRetry).toHaveBeenCalledTimes(1);
    });

    it("calls onDismiss when Dismiss is clicked", async () => {
        const onDismiss = vi.fn();
        const user = userEvent.setup();
        render(<UploadFailureNotice failed={failed} onRetry={vi.fn()} onDismiss={onDismiss} />);

        await user.click(screen.getByRole("button", { name: "Dismiss" }));

        expect(onDismiss).toHaveBeenCalledTimes(1);
    });

    it("disables both buttons while retrying", () => {
        render(<UploadFailureNotice failed={failed} onRetry={vi.fn()} onDismiss={vi.fn()} retrying />);

        expect(screen.getByRole("button", { name: "Retrying..." })).toBeDisabled();
        expect(screen.getByRole("button", { name: "Dismiss" })).toBeDisabled();
    });
});
