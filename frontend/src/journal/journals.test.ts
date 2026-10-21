import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
    createJournalEntry,
    deleteJournalEntry,
    DuplicateDateError,
    getJournal,
    getJournals,
    updateJournalEntry,
} from "./journals";
import { API_BASE_URL } from "../shared/config";
import { jsonResponse, makeJournal } from "../test/factories";

const fetchMock = vi.fn<typeof fetch>();

function calledUrl(): URL {
    return new URL(fetchMock.mock.calls[0][0] as string);
}

describe("journals client", () => {
    beforeEach(() => {
        vi.stubGlobal("fetch", fetchMock);
    });

    afterEach(() => {
        fetchMock.mockReset();
        vi.unstubAllGlobals();
    });

    describe("getJournal", () => {
        it("fetches one entry with credentials", async () => {
            fetchMock.mockResolvedValue(jsonResponse(makeJournal()));

            await expect(getJournal("1")).resolves.toEqual(makeJournal());
            expect(fetchMock).toHaveBeenCalledWith(`${API_BASE_URL}/journals/1`, { credentials: "include" });
        });

        it("throws when the entry isn't found", async () => {
            fetchMock.mockResolvedValue(jsonResponse({ detail: "Not Found" }, 404));

            await expect(getJournal("1")).rejects.toThrow("404");
        });
    });

    describe("getJournals", () => {
        it("sends only the filters it was given", async () => {
            fetchMock.mockResolvedValue(jsonResponse([]));

            await getJournals(3, 1);

            const url = calledUrl();
            expect(url.pathname).toBe("/journals/");
            expect(Object.fromEntries(url.searchParams)).toEqual({ month: "3", day: "1" });
            expect(fetchMock.mock.calls[0][1]).toMatchObject({ credentials: "include" });
        });

        it("includes the year when given", async () => {
            fetchMock.mockResolvedValue(jsonResponse([]));

            await getJournals(3, 1, 2025);

            expect(calledUrl().searchParams.get("year")).toBe("2025");
        });

        it("sends no filters when called without any", async () => {
            fetchMock.mockResolvedValue(jsonResponse([]));

            await getJournals();

            expect(calledUrl().search).toBe("");
        });

        it("throws on failure", async () => {
            fetchMock.mockResolvedValue(jsonResponse({}, 500));

            await expect(getJournals(3, 1)).rejects.toThrow("Failed to load journals: 500");
        });
    });

    describe("createJournalEntry", () => {
        it("posts date and message as query params", async () => {
            fetchMock.mockResolvedValue(jsonResponse(makeJournal(), 201));

            await expect(createJournalEntry("2025-07-25", "Hi & bye")).resolves.toEqual(makeJournal());

            const url = calledUrl();
            expect(url.searchParams.get("date")).toBe("2025-07-25");
            expect(url.searchParams.get("message")).toBe("Hi & bye");
            expect(fetchMock.mock.calls[0][1]).toEqual({ method: "POST", credentials: "include" });
        });

        it("throws DuplicateDateError on 409", async () => {
            fetchMock.mockResolvedValue(jsonResponse({}, 409));

            await expect(createJournalEntry("2025-07-25", "Again")).rejects.toBeInstanceOf(DuplicateDateError);
        });

        it("throws a plain error on other failures", async () => {
            fetchMock.mockResolvedValue(jsonResponse({}, 500));

            const error = await createJournalEntry("2025-07-25", "Hi").catch((e: unknown) => e);
            expect(error).not.toBeInstanceOf(DuplicateDateError);
            expect(error).toEqual(new Error("Failed to create journal entry: 500"));
        });
    });

    describe("updateJournalEntry", () => {
        it("puts the date as input_date, matching the backend's parameter name", async () => {
            fetchMock.mockResolvedValue(jsonResponse(makeJournal()));

            await updateJournalEntry("1", "2025-07-26", "Edited");

            const url = calledUrl();
            expect(url.pathname).toBe("/journals/1");
            expect(Object.fromEntries(url.searchParams)).toEqual({ input_date: "2025-07-26", message: "Edited" });
            expect(fetchMock.mock.calls[0][1]).toEqual({ method: "PUT", credentials: "include" });
        });

        it("throws DuplicateDateError on 409", async () => {
            fetchMock.mockResolvedValue(jsonResponse({}, 409));

            await expect(updateJournalEntry("1", "2025-07-26", "Edited")).rejects.toBeInstanceOf(DuplicateDateError);
        });

        it("throws on other failures", async () => {
            fetchMock.mockResolvedValue(jsonResponse({}, 404));

            await expect(updateJournalEntry("1", "2025-07-26", "Edited")).rejects.toThrow(
                "Failed to update journal entry: 404",
            );
        });
    });

    describe("deleteJournalEntry", () => {
        it("sends a DELETE", async () => {
            fetchMock.mockResolvedValue(new Response(null, { status: 204 }));

            await deleteJournalEntry("1");

            expect(fetchMock).toHaveBeenCalledWith(`${API_BASE_URL}/journals/1`, {
                method: "DELETE",
                credentials: "include",
            });
        });

        it("throws on failure", async () => {
            fetchMock.mockResolvedValue(jsonResponse({}, 404));

            await expect(deleteJournalEntry("1")).rejects.toThrow("Failed to delete journal entry: 404");
        });
    });
});
