import { useStore } from "../store";

export function ScenarioPicker() {
  const { scenarios, selectedId, selectScenario } = useStore();

  return (
    <section className="card">
      <h2>Demo scenarios</h2>
      <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "var(--space-4)" }}>
        Hand-tuned Indonesian geothermal questions. Pick one, then hit Ask.
      </p>
      <div className="stack">
        {scenarios.map((s) => {
          const active = s.id === selectedId;
          return (
            <button
              key={s.id}
              onClick={() => selectScenario(s.id)}
              className="scenario-btn"
              style={{
                textAlign: "left",
                background: active ? "var(--accent-soft)" : "var(--bg-sunken)",
                borderLeft: `3px solid ${active ? "var(--accent)" : "transparent"}`,
                border: "1px solid var(--border-subtle)",
                borderLeftWidth: "3px",
                borderLeftColor: active ? "var(--accent)" : "transparent",
                borderRadius: "var(--radius-md)",
                padding: "var(--space-3) var(--space-4)",
                cursor: "pointer",
                transition: "background 120ms ease",
              }}
            >
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "var(--text-xs)",
                  color: "var(--fg-subtle)",
                  marginBottom: "var(--space-1)",
                }}
              >
                {s.id}
              </div>
              <div
                style={{
                  fontFamily: "var(--font-serif)",
                  fontSize: "var(--text-base)",
                  color: "var(--fg)",
                  lineHeight: "var(--leading-normal)",
                }}
              >
                {s.question}
              </div>
            </button>
          );
        })}
        {scenarios.length === 0 && (
          <p className="subtle" style={{ fontSize: "var(--text-sm)" }}>
            Loading scenarios…
          </p>
        )}
      </div>
    </section>
  );
}
