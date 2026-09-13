import { API_BASE_URL } from "./config";

export interface User {
    id: string;
    name: string;
    email: string;
}

async function parseUserOrThrow(response: Response, failureMessage: string): Promise<User> {
    if (!response.ok) {
        throw new Error(failureMessage);
    }
    return (await response.json()) as User;
}

export async function signup(name: string, email: string, password: string): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/auth/signup`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password }),
    });

    return parseUserOrThrow(response, "Failed to sign up");
}

export async function login(email: string, password: string): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
    });

    return parseUserOrThrow(response, "Invalid email or password");
}

export async function logout(): Promise<void> {
    await fetch(`${API_BASE_URL}/auth/logout`, {
        method: "POST",
        credentials: "include",
    });
}

export async function getCurrentUser(): Promise<User | null> {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
        credentials: "include",
    });

    if (response.status === 401) {
        return null;
    }
    if (!response.ok) {
        throw new Error("Failed to load current user");
    }

    return (await response.json()) as User;
}
