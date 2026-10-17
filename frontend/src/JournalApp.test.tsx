import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { JournalApp } from "./JournalApp";
import { useAuth } from "./AuthContext";
import { getJournals, createJournalEntry, deleteJournalEntry } from "./journals";
import type { Journal } from "./models";

vi.mock("./AuthContext", () => ({
    useAuth: vi.fn(),
}));

vi.mock("./journals", () => ({
    getJournals: vi.fn(),
    createJournalEntry: vi.fn(),
    updateJournalEntry: vi.fn(),
    deleteJournalEntry: vi.fn(),
}));

const mockedUseAuth = vi.mocked(useAuth);
const mockedGetJournals = vi.mocked(getJournals);
const mockedCreateJournalEntry = vi.mocked(createJournalEntry);
const mockedDeleteJournalEntry = vi.mocked(deleteJournalEntry);

function makeJournal(overrides: Partial<Journal> = {}): Journal {
    return {
        id: "1",
        author_id: "author-1",
        date: "2025-07-25",
        message: "Had a great day",
        ...overrides,
    };
}

describe("JournalApp", () => {
    beforeEach(() => {
        mockedUseAuth.mockReturnValue({
            user: { id: "author-1", name: "Alice", email: "alice@example.com" },
            loading: false,
            login: vi.fn(),
            signup: vi.fn(),
            logout: vi.fn(),
        });
        mockedGetJournals.mockReset();
        mockedCreateJournalEntry.mockReset();
        mockedDeleteJournalEntry.mockReset();
    });

    it("renders entries returned for the selected day", async () => {
        mockedGetJournals.mockResolvedValue([makeJournal({ message: "Had a great day" })]);
        render(<JournalApp />);

        expect(await screen.findByText("Had a great day")).toBeInTheDocument();
    });

    it("shows an error when loading entries fails", async () => {
        mockedGetJournals.mockRejectedValue(new Error("network down"));
        render(<JournalApp />);

        expect(await screen.findByText("Failed to load entries for this day.")).toBeInTheDocument();
    });

    it("adds a new entry to the list on successful submit", async () => {
        mockedGetJournals.mockResolvedValue([]);
        mockedCreateJournalEntry.mockResolvedValue(makeJournal({ id: "2", message: "New entry" }));
        const user = userEvent.setup();
        render(<JournalApp />);

        await waitFor(() => expect(mockedGetJournals).toHaveBeenCalled());

        await user.type(screen.getByPlaceholderText("Write a new entry for this day..."), "New entry");
        await user.click(screen.getByRole("button", { name: "Send" }));

        expect(await screen.findByText("New entry")).toBeInTheDocument();
        expect(mockedCreateJournalEntry).toHaveBeenCalledWith(expect.any(String), "New entry");
    });

    it("removes an entry from the list after a successful delete", async () => {
        mockedGetJournals.mockResolvedValue([makeJournal({ message: "Delete me" })]);
        mockedDeleteJournalEntry.mockResolvedValue(undefined);
        vi.spyOn(window, "confirm").mockReturnValue(true);
        const user = userEvent.setup();
        render(<JournalApp />);

        await screen.findByText("Delete me");
        await user.click(screen.getByRole("button", { name: "Delete" }));

        await waitFor(() => expect(screen.queryByText("Delete me")).not.toBeInTheDocument());
    });
});
