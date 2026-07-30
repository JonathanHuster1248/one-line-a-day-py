import { useEffect, useState } from "react";
import { getGreeting } from "./greeting";

export default function App() {
    const [greeting, setGreeting] = useState("Loading...");

    useEffect(() => {
        async function loadGreeting() {
            const value = await getGreeting();
            setGreeting(value);
        }

        loadGreeting();
    }, []);

    return (
        <h1>{greeting}</h1>
    );
}