import { useEffect, useState } from "react";
import { Header } from "./components/Header";
import { ScenarioPicker } from "./components/ScenarioPicker";
import { QueryInput } from "./components/QueryInput";
import { AgentTrace } from "./components/AgentTrace";
import { AnswerPanel } from "./components/AnswerPanel";
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
      <div className="grid-two">
        <div className="stack" style={{ gap: "var(--space-6)" }}>
          <ScenarioPicker />
          <QueryInput />
        </div>
        <div className="stack" style={{ gap: "var(--space-6)" }}>
          <FieldPanel />
          <AnswerPanel />
          <AgentTrace />
        </div>
      </div>
      <footer className="subtle" style={{ fontSize: "var(--text-xs)", textAlign: "center" }}>
        Built for the Opus 4.7 hackathon. GeoForce-Solver (implicit Darcy + energy) +
        v1.1 ReservoirCNN surrogate.
      </footer>
    </div>
  );
}
