import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthForms } from "./AuthForms";
import { useAuth } from "./AuthContext";
import { EmailTakenError } from "./auth";

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

    async function submitSignup() {
        const user = userEvent.setup();
        render(<AuthForms />);
        await user.click(screen.getByText("Need an account? Sign up"));
        await user.type(screen.getByPlaceholderText("Name"), "Alice");
        await user.type(screen.getByPlaceholderText("Email"), "alice@example.com");
        await user.type(screen.getByPlaceholderText("Password"), "hunter2");
        await user.click(screen.getByRole("button", { name: "Sign Up" }));
        return user;
    }

    it("says when the email is already registered", async () => {
        signup.mockRejectedValue(new EmailTakenError());
        await submitSignup();

        expect(await screen.findByText("That email is already registered.")).toBeInTheDocument();
    });

    it("shows a generic message for other signup failures", async () => {
        signup.mockRejectedValue(new Error("boom"));
        await submitSignup();

        expect(await screen.findByText("Failed to sign up")).toBeInTheDocument();
    });

    it("clears the error when switching modes", async () => {
        signup.mockRejectedValue(new Error("boom"));
        const user = await submitSignup();
        await screen.findByText("Failed to sign up");

        await user.click(screen.getByText("Already have an account? Log in"));

        expect(screen.queryByText("Failed to sign up")).not.toBeInTheDocument();
        expect(screen.getByRole("heading", { name: "Log In" })).toBeInTheDocument();
    });
});
