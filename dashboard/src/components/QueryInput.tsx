import { useStore } from "../store";

export function QueryInput() {
  const query = useStore((s) => s.query);
  const selectedId = useStore((s) => s.selectedId);
  const sending = useStore((s) => s.sending);
  const sessionStarting = useStore((s) => s.sessionStarting);
  const messages = useStore((s) => s.messages);
  const setQuery = useStore((s) => s.setQuery);
  const sendMessage = useStore((s) => s.sendMessage);

  const busy = sending || sessionStarting;
  const hasChat = messages.length > 0;

  async function onSend() {
    const text = query.trim();
    if (!text || busy) return;
    // Attach scenario_id only on the first turn — the server prepends the
    // scenario question once; follow-ups are pure text against the same
    // multi-turn context.
    const scenarioForTurn = hasChat ? undefined : selectedId;
    setQuery("");
    await sendMessage(text, scenarioForTurn);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Enter submits, Shift+Enter newlines.
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void onSend();
    }
  }

  return (
    <section className="card">
      <h2>{hasChat ? "Follow up" : "Ask the agent"}</h2>
      <p
        className="muted"
        style={{
          fontSize: "var(--text-sm)",
          marginBottom: "var(--space-4)",
        }}
      >
        {hasChat
          ? "The model sees prior turns — ask for Monte Carlo, sensitivity sweeps, or probe another cell."
          : "The agent will decompose your question, dispatch the solver and surrogate, and — if asked — run a Monte Carlo ensemble or sensitivity sweep."}
      </p>
      <label className="label" htmlFor="q">
        Question
      </label>
      <textarea
        id="q"
        className="textarea"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder={
          hasChat
            ? "e.g. Now run a 200-sample Monte Carlo with ±20% permeability."
            : "e.g. What temperature would we hit at 1500 m below site Kamojang-7?"
        }
      />
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: "var(--space-4)",
          gap: "var(--space-3)",
        }}
      >
        <span className="subtle" style={{ fontSize: "var(--text-xs)" }}>
          {hasChat
            ? "multi-turn session"
            : selectedId
              ? `scenario: ${selectedId}`
              : "free-form query"}
        </span>
        <button
          className="btn-primary"
          onClick={() => void onSend()}
          disabled={busy || query.trim().length === 0}
        >
          {sessionStarting
            ? "Opening session…"
            : sending
              ? "Running…"
              : hasChat
                ? "Send"
                : "Ask agent"}
        </button>
      </div>
    </section>
  );
}
