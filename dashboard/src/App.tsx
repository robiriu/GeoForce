import { useEffect, useState } from "react";
import { Header } from "./components/Header";
import { ScenarioPicker } from "./components/ScenarioPicker";
import { QueryInput } from "./components/QueryInput";
import { ChatThread } from "./components/ChatThread";
import { FieldPanel } from "./components/FieldPanel";
import { checkHealth, fetchScenarios } from "./api/client";
import { useStore } from "./store";

export default function App() {
  const setScenarios = useStore((s) => s.setScenarios);
  const [healthy, setHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    checkHealth().then(setHealthy);
    fetchScenarios()
      .then(setScenarios)
      .catch((err) => console.error("scenarios load failed", err));
  }, [setScenarios]);

  return (
    <div className="app-shell">
      <Header healthy={healthy} />

      {/* Hero: scenario cards on the left, side-by-side canvas on the right.
          First impression; preserved across chat turns. */}
      <div className="grid-two">
        <ScenarioPicker />
        <FieldPanel />
      </div>

      {/* Conversation (appears after the first turn) + persistent composer. */}
      <div className="stack" style={{ gap: "var(--space-6)" }}>
        <ChatThread />
        <QueryInput />
      </div>

      <footer
        style={{
          fontSize: "var(--text-xs)",
          textAlign: "center",
          color: "var(--fg-subtle)",
          borderTop: "1px solid var(--border-subtle)",
          paddingTop: "var(--space-4)",
        }}
      >
        <span style={{ color: "var(--accent)" }}>GeoForce</span> by ForceX AI
        &middot; GeoForce-Solver + ReservoirCNN v1.1 surrogate
      </footer>
    </div>
  );
}
