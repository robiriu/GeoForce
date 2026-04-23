import { useStore } from "../store";

export function AgentTrace() {
  const { trace, running, error } = useStore();

  return (
    <section className="card">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: "var(--space-4)",
        }}
      >
        <h2>Agent trace</h2>
        <span className="subtle" style={{ fontSize: "var(--text-xs)" }}>
          {running ? "streaming…" : `${trace.length} events`}
        </span>
      </div>

      {error && (
        <div
          style={{
            background: "var(--bg-sunken)",
            borderLeft: "2px solid var(--danger)",
            padding: "var(--space-3) var(--space-4)",
            borderRadius: "var(--radius-sm)",
            color: "var(--danger)",
            fontSize: "var(--text-sm)",
            marginBottom: "var(--space-4)",
          }}
        >
          {error}
        </div>
      )}

      {trace.length === 0 && !running && (
        <p className="subtle" style={{ fontSize: "var(--text-sm)" }}>
          No trace yet. Ask a scenario to watch the agent call tools.
        </p>
      )}

      <div className="stack">
        {trace.map((item, i) =>
          item.kind === "tool" ? (
            <ToolCard key={i} name={item.name} input={item.input} />
          ) : (
            <TextCard key={i} text={item.text} />
          ),
        )}
      </div>
    </section>
  );
}

function ToolCard({ name, input }: { name: string; input: Record<string, unknown> }) {
  const shortName = name.replace(/^mcp__geoforce__/, "");
  return (
    <div
      style={{
        background: "var(--bg-elevated)",
        border: "1px solid var(--border-subtle)",
        borderLeft: "2px solid var(--accent)",
        borderRadius: "var(--radius-sm)",
        padding: "var(--space-3) var(--space-4)",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: "var(--space-3)",
          marginBottom: "var(--space-2)",
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-serif)",
            fontStyle: "italic",
            color: "var(--fg)",
            fontSize: "var(--text-sm)",
          }}
        >
          tool call
        </span>
        <code
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "var(--text-sm)",
            color: "var(--accent-hover)",
          }}
        >
          {shortName}
        </code>
      </div>
      <pre
        style={{
          margin: 0,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          color: "var(--fg-muted)",
          fontSize: "var(--text-xs)",
          fontFamily: "var(--font-mono)",
        }}
      >
        {safeJson(input)}
      </pre>
    </div>
  );
}

function TextCard({ text }: { text: string }) {
  return (
    <div
      style={{
        background: "var(--bg-elevated)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-sm)",
        padding: "var(--space-3) var(--space-4)",
        color: "var(--fg)",
        fontSize: "var(--text-sm)",
        lineHeight: "var(--leading-normal)",
        whiteSpace: "pre-wrap",
      }}
    >
      {text}
    </div>
  );
}

function safeJson(obj: unknown): string {
  try {
    const s = JSON.stringify(obj, null, 2);
    return s.length > 800 ? s.slice(0, 800) + "\n…" : s;
  } catch {
    return String(obj);
  }
}
