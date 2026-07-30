import { getGreeting } from "./greeting";

export default function App() {
    return (
        <h1>{getGreeting()}</h1>
    );
}