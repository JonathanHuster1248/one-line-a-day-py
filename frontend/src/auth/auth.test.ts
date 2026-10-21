import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { EmailTakenError, getCurrentUser, login, logout, signup } from "./auth";
import { API_BASE_URL } from "../shared/config";
import { jsonResponse, makeUser } from "../test/factories";

const alice = makeUser();

const fetchMock = vi.fn<typeof fetch>();

describe("auth client", () => {
    beforeEach(() => {
        vi.stubGlobal("fetch", fetchMock);
    });

    afterEach(() => {
        fetchMock.mockReset();
        vi.unstubAllGlobals();
    });

    describe("signup", () => {
        it("posts name, email, and password as JSON with credentials", async () => {
            fetchMock.mockResolvedValue(jsonResponse(alice, 201));

            await expect(signup("Alice", "alice@example.com", "hunter22")).resolves.toEqual(alice);

            const [url, init] = fetchMock.mock.calls[0];
            expect(url).toBe(`${API_BASE_URL}/auth/signup`);
            expect(init).toMatchObject({
                method: "POST",
                credentials: "include",
                headers: { "Content-Type": "application/json" },
            });
            expect(JSON.parse(init?.body as string)).toEqual({
                name: "Alice",
                email: "alice@example.com",
                password: "hunter22",
            });
        });

        it("throws EmailTakenError on 409", async () => {
            fetchMock.mockResolvedValue(jsonResponse({ detail: "Email already registered" }, 409));

            await expect(signup("Alice", "alice@example.com", "hunter22")).rejects.toBeInstanceOf(EmailTakenError);
        });

        it("throws a generic error on other failures", async () => {
            fetchMock.mockResolvedValue(jsonResponse({}, 500));

            const error = await signup("Alice", "alice@example.com", "hunter22").catch((e: unknown) => e);
            expect(error).not.toBeInstanceOf(EmailTakenError);
            expect(error).toEqual(new Error("Failed to sign up"));
        });
    });

    describe("login", () => {
        it("posts email and password as JSON with credentials", async () => {
            fetchMock.mockResolvedValue(jsonResponse(alice, 201));

            await expect(login("alice@example.com", "hunter22")).resolves.toEqual(alice);

            const [url, init] = fetchMock.mock.calls[0];
            expect(url).toBe(`${API_BASE_URL}/auth/login`);
            expect(init).toMatchObject({ method: "POST", credentials: "include" });
            expect(JSON.parse(init?.body as string)).toEqual({ email: "alice@example.com", password: "hunter22" });
        });

        it("throws on bad credentials", async () => {
            fetchMock.mockResolvedValue(jsonResponse({}, 401));

            await expect(login("alice@example.com", "wrong")).rejects.toThrow("Invalid email or password");
        });
    });

    describe("logout", () => {
        it("posts to logout with credentials", async () => {
            fetchMock.mockResolvedValue(new Response(null, { status: 201 }));

            await logout();

            expect(fetchMock).toHaveBeenCalledWith(`${API_BASE_URL}/auth/logout`, {
                method: "POST",
                credentials: "include",
            });
        });
    });

    describe("getCurrentUser", () => {
        it("returns the user when the session is valid", async () => {
            fetchMock.mockResolvedValue(jsonResponse(alice));

            await expect(getCurrentUser()).resolves.toEqual(alice);
            expect(fetchMock).toHaveBeenCalledWith(`${API_BASE_URL}/auth/me`, { credentials: "include" });
        });

        it("returns null when not logged in", async () => {
            fetchMock.mockResolvedValue(jsonResponse({}, 401));

            await expect(getCurrentUser()).resolves.toBeNull();
        });

        it("throws on other failures", async () => {
            fetchMock.mockResolvedValue(jsonResponse({}, 500));

            await expect(getCurrentUser()).rejects.toThrow("Failed to load current user");
        });
    });
});
