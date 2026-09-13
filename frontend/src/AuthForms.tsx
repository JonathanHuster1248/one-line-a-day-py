import { useState } from "react";
import { useAuth } from "./AuthContext";

export function AuthForms() {
    const [mode, setMode] = useState<"login" | "signup">("login");
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const { login, signup } = useAuth();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setIsSubmitting(true);
        try {
            if (mode === "login") {
                await login(email, password);
            } else {
                await signup(name, email, password);
            }
        } catch {
            setError(mode === "login" ? "Invalid email or password" : "Failed to sign up");
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="auth-forms">
            <h2>{mode === "login" ? "Log In" : "Sign Up"}</h2>
            <form onSubmit={handleSubmit}>
                {mode === "signup" && (
                    <input
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="Name"
                        required
                    />
                )}
                <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Email"
                    required
                />
                <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Password"
                    required
                />
                <button type="submit" disabled={isSubmitting}>
                    {mode === "login" ? "Log In" : "Sign Up"}
                </button>
            </form>
            {error && <p className="auth-error">{error}</p>}
            <button
                type="button"
                onClick={() => {
                    setError(null);
                    setMode(mode === "login" ? "signup" : "login");
                }}
            >
                {mode === "login" ? "Need an account? Sign up" : "Already have an account? Log in"}
            </button>
        </div>
    );
}
