import { useAuth } from "./AuthContext";
import { AuthForms } from "./AuthForms";
import { JournalApp } from "./JournalApp";

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
