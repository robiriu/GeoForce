import { useStore } from "../store";
import { streamQuery } from "../api/client";

export function QueryInput() {
  const {
    query,
    selectedId,
    running,
    setQuery,
    beginRun,
    pushEvent,
    endRun,
    setError,
  } = useStore();

  async function onRun() {
    beginRun();
    try {
      await streamQuery(
        { query, scenario_id: selectedId ?? undefined },
        (e) => pushEvent(e),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      endRun();
    }
  }

  return (
    <section className="card">
      <h2>Ask the agent</h2>
      <p className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "var(--space-4)" }}>
        The agent will decompose your question, dispatch the solver and surrogate, and — if
        asked — run a Monte Carlo ensemble or sensitivity sweep.
      </p>
      <label className="label" htmlFor="q">
        Question
      </label>
      <textarea
        id="q"
        className="textarea"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="e.g. What temperature would we hit at 1500 m below site Kamojang-7?"
      />
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: "var(--space-4)",
        }}
      >
        <span className="subtle" style={{ fontSize: "var(--text-xs)" }}>
          {selectedId ? `scenario: ${selectedId}` : "free-form query"}
        </span>
        <button
          className="btn-primary"
          onClick={onRun}
          disabled={running || query.trim().length === 0}
        >
          {running ? "Running…" : "Ask agent"}
        </button>
      </div>
    </section>
  );
}
