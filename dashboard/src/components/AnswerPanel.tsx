import { useStore } from "../store";

export function AnswerPanel() {
  const { finalText, stopReason, running } = useStore();

  if (!finalText && !running) return null;

  return (
    <section
      className="card"
      style={{
        borderLeft: "3px solid var(--accent)",
        background: "var(--bg-elevated)",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: "var(--space-3)",
        }}
      >
        <h2>Answer</h2>
        {stopReason && (
          <span className="subtle" style={{ fontSize: "var(--text-xs)" }}>
            stop: {stopReason}
          </span>
        )}
      </div>
      {finalText ? (
        <p
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: "var(--text-lg)",
            lineHeight: "var(--leading-loose)",
            whiteSpace: "pre-wrap",
            color: "var(--fg)",
          }}
        >
          {finalText}
        </p>
      ) : (
        <p className="subtle" style={{ fontSize: "var(--text-sm)" }}>
          Agent is still reasoning…
        </p>
      )}
    </section>
  );
}
