import { useAuth } from "./auth/AuthContext";
import { AuthForms } from "./auth/AuthForms";
import { JournalApp } from "./journal/JournalApp";

export default function App() {
    const { user, loading } = useAuth();

    if (loading) {
        return <div>Loading...</div>;
    }

    if (!user) {
        return <AuthForms />;
    }

    return <JournalApp />;
}
