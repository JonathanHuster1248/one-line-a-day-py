import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, renderHook, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import { AuthProvider, useAuth } from "./AuthContext";
import { getCurrentUser, login, logout, signup, type User } from "./auth";

vi.mock("./auth", async (importOriginal) => ({
    EmailTakenError: (await importOriginal<typeof import("./auth")>()).EmailTakenError,
    getCurrentUser: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
    signup: vi.fn(),
}));

// The journal page has its own tests; here it only needs to show who's logged in and log out.
vi.mock("./JournalApp", () => ({
    JournalApp: () => {
        const { user, logout } = useAuth();
        return (
            <div>
                <p>Journal for {user?.name}</p>
                <button type="button" onClick={() => logout()}>
                    Log Out
                </button>
            </div>
        );
    },
}));

const mockedGetCurrentUser = vi.mocked(getCurrentUser);
const mockedLogin = vi.mocked(login);
const mockedLogout = vi.mocked(logout);
const mockedSignup = vi.mocked(signup);

const alice: User = { id: "u1", name: "Alice", email: "alice@example.com" };

function renderApp() {
    const user = userEvent.setup();
    render(
        <AuthProvider>
            <App />
        </AuthProvider>,
    );
    return user;
}

describe("App auth gate", () => {
    beforeEach(() => {
        mockedGetCurrentUser.mockReset();
        mockedLogin.mockReset();
        mockedLogout.mockReset().mockResolvedValue(undefined);
        mockedSignup.mockReset();
    });

    it("shows a loading state until the session check finishes", async () => {
        let resolve!: (user: User | null) => void;
        mockedGetCurrentUser.mockReturnValue(new Promise((r) => (resolve = r)));
        renderApp();

        expect(screen.getByText("Loading...")).toBeInTheDocument();
        expect(screen.queryByPlaceholderText("Email")).not.toBeInTheDocument();

        resolve(null);
        expect(await screen.findByRole("heading", { name: "Log In" })).toBeInTheDocument();
    });

    it("shows the journal when a session already exists", async () => {
        mockedGetCurrentUser.mockResolvedValue(alice);
        renderApp();

        expect(await screen.findByText("Journal for Alice")).toBeInTheDocument();
    });

    it("shows the login form when the session check fails", async () => {
        mockedGetCurrentUser.mockRejectedValue(new Error("network down"));
        renderApp();

        expect(await screen.findByRole("heading", { name: "Log In" })).toBeInTheDocument();
    });

    it("logs in, then logs out back to the login form", async () => {
        mockedGetCurrentUser.mockResolvedValue(null);
        mockedLogin.mockResolvedValue(alice);
        const user = renderApp();

        await screen.findByRole("heading", { name: "Log In" });
        await user.type(screen.getByPlaceholderText("Email"), "alice@example.com");
        await user.type(screen.getByPlaceholderText("Password"), "hunter22");
        await user.click(screen.getByRole("button", { name: "Log In" }));

        expect(await screen.findByText("Journal for Alice")).toBeInTheDocument();
        expect(mockedLogin).toHaveBeenCalledWith("alice@example.com", "hunter22");

        await user.click(screen.getByRole("button", { name: "Log Out" }));

        expect(await screen.findByRole("heading", { name: "Log In" })).toBeInTheDocument();
        expect(mockedLogout).toHaveBeenCalled();
    });

    it("signs up straight into the journal", async () => {
        mockedGetCurrentUser.mockResolvedValue(null);
        mockedSignup.mockResolvedValue(alice);
        const user = renderApp();

        await user.click(await screen.findByText("Need an account? Sign up"));
        await user.type(screen.getByPlaceholderText("Name"), "Alice");
        await user.type(screen.getByPlaceholderText("Email"), "alice@example.com");
        await user.type(screen.getByPlaceholderText("Password"), "hunter22");
        await user.click(screen.getByRole("button", { name: "Sign Up" }));

        expect(await screen.findByText("Journal for Alice")).toBeInTheDocument();
    });

    it("stays on the login form when login fails", async () => {
        mockedGetCurrentUser.mockResolvedValue(null);
        mockedLogin.mockRejectedValue(new Error("Invalid email or password"));
        const user = renderApp();

        await screen.findByRole("heading", { name: "Log In" });
        await user.type(screen.getByPlaceholderText("Email"), "alice@example.com");
        await user.type(screen.getByPlaceholderText("Password"), "wrong");
        await user.click(screen.getByRole("button", { name: "Log In" }));

        expect(await screen.findByText("Invalid email or password")).toBeInTheDocument();
        expect(screen.queryByText(/Journal for/)).not.toBeInTheDocument();
    });

    it("useAuth throws outside an AuthProvider", () => {
        vi.spyOn(console, "error").mockImplementation(() => {});
        expect(() => renderHook(() => useAuth())).toThrow("useAuth must be used within an AuthProvider");
    });
});
