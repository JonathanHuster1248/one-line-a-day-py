import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthForms } from "./AuthForms";
import { useAuth } from "./AuthContext";

vi.mock("./AuthContext", () => ({
    useAuth: vi.fn(),
}));

const mockedUseAuth = vi.mocked(useAuth);

describe("AuthForms", () => {
    const login = vi.fn();
    const signup = vi.fn();

    beforeEach(() => {
        login.mockReset();
        signup.mockReset();
        mockedUseAuth.mockReturnValue({
            user: null,
            loading: false,
            login,
            signup,
            logout: vi.fn(),
        });
    });

    it("logs in with the entered email and password", async () => {
        login.mockResolvedValue(undefined);
        const user = userEvent.setup();
        render(<AuthForms />);

        await user.type(screen.getByPlaceholderText("Email"), "alice@example.com");
        await user.type(screen.getByPlaceholderText("Password"), "hunter2");
        await user.click(screen.getByRole("button", { name: "Log In" }));

        await waitFor(() => expect(login).toHaveBeenCalledWith("alice@example.com", "hunter2"));
    });

    it("shows an error message when login fails", async () => {
        login.mockRejectedValue(new Error("nope"));
        const user = userEvent.setup();
        render(<AuthForms />);

        await user.type(screen.getByPlaceholderText("Email"), "alice@example.com");
        await user.type(screen.getByPlaceholderText("Password"), "wrong");
        await user.click(screen.getByRole("button", { name: "Log In" }));

        expect(await screen.findByText("Invalid email or password")).toBeInTheDocument();
    });

    it("switches to signup mode and submits name, email, and password", async () => {
        signup.mockResolvedValue(undefined);
        const user = userEvent.setup();
        render(<AuthForms />);

        await user.click(screen.getByText("Need an account? Sign up"));
        await user.type(screen.getByPlaceholderText("Name"), "Alice");
        await user.type(screen.getByPlaceholderText("Email"), "alice@example.com");
        await user.type(screen.getByPlaceholderText("Password"), "hunter2");
        await user.click(screen.getByRole("button", { name: "Sign Up" }));

        await waitFor(() =>
            expect(signup).toHaveBeenCalledWith("Alice", "alice@example.com", "hunter2")
        );
    });
});
