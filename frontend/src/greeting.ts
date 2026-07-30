export async function getGreeting(): Promise<string> {
    const response = await fetch("http://localhost:8000/hello_world");
    // const response = await fetch("http://localhost:8000/jourunals/20f06456-00e3-47f8-a6e1-cbcb2d31bb20");

    return await response.text();
}