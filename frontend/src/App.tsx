import { useEffect, useState } from "react";

export default function App() {
  const [hash, setHash] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    fetch("/health", { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Health request failed: ${response.status}`);
        const health = await response.json();
        if (health.status !== "ok" || typeof health.arms_hash !== "string") {
          throw new Error("Invalid health response");
        }
        setHash(health.arms_hash);
      })
      .catch((err) => {
        if (!controller.signal.aborted) setError(String(err));
      });
    return () => controller.abort();
  }, []);

  return (
    <main>
      <h1>Scaffolded Answer Engine</h1>
      {error ? <p role="alert">{error}</p> :
        <p role="status">{hash ? `Arms hash: ${hash}` : "Checking service…"}</p>}
    </main>
  );
}
