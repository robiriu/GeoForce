import { useEffect, useRef } from "react";
import { useStore } from "../store";
import type { ChatMessage, TraceItem } from "../store";

export function ChatThread() {
  const messages = useStore((s) => s.messages);
  const error = useStore((s) => s.error);
  const resetChat = useStore((s) => s.resetChat);
  const sessionId = useStore((s) => s.sessionId);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  if (messages.length === 0 && !error) return null;

  return (
    <section
      className="card"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-4)",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
        }}
      >
        <h2>Conversation</h2>
        <div
          style={{
            display: "flex",
            gap: "var(--space-3)",
            alignItems: "baseline",
          }}
        >
          {sessionId && (
            <span
              className="subtle"
              style={{ fontSize: "var(--text-xs)", fontFamily: "var(--font-mono)" }}
              title="Multi-turn session id (server keeps the ClaudeSDKClient alive so the model sees prior turns)."
            >
              session {sessionId.slice(0, 8)}
            </span>
          )}
          {messages.length > 0 && (
            <button
              onClick={() => void resetChat()}
              style={{
                background: "transparent",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-sm)",
                padding: "var(--space-1) var(--space-3)",
                fontFamily: "var(--font-mono)",
                fontSize: "var(--text-xs)",
                color: "var(--fg-subtle)",
                cursor: "pointer",
              }}
              title="Close the session and clear the chat."
            >
              new chat
            </button>
          )}
        </div>
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
          }}
        >
          {error}
        </div>
      )}

      <div className="stack" style={{ gap: "var(--space-4)" }}>
        {messages.map((m) => (
          <Bubble key={m.id} msg={m} />
        ))}
      </div>
      <div ref={endRef} />
    </section>
  );
}

function Bubble({ msg }: { msg: ChatMessage }) {
  if (msg.role === "user") {
    return (
      <div
        style={{
          alignSelf: "flex-end",
          maxWidth: "85%",
          background: "var(--accent-soft)",
          border: "1px solid var(--accent)",
          borderRadius: "var(--radius-lg)",
          padding: "var(--space-3) var(--space-4)",
          fontFamily: "var(--font-serif)",
          fontSize: "var(--text-base)",
          color: "var(--fg)",
          whiteSpace: "pre-wrap",
          marginLeft: "auto",
        }}
      >
        {msg.text}
      </div>
    );
  }

  return (
    <div
      style={{
        background: "var(--bg-elevated)",
        border: "1px solid var(--border-subtle)",
        borderLeft: "3px solid var(--accent)",
        borderRadius: "var(--radius-lg)",
        padding: "var(--space-4)",
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-3)",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
        }}
      >
        <span className="label">GeoForce agent</span>
        <span
          className="subtle"
          style={{ fontSize: "var(--text-xs)", fontFamily: "var(--font-mono)" }}
        >
          {msg.running
            ? "streaming…"
            : msg.stopReason
              ? `stop: ${msg.stopReason}`
              : `${msg.trace.length} events`}
        </span>
      </div>

      {msg.trace.length > 0 && (
        <div className="stack" style={{ gap: "var(--space-2)" }}>
          {msg.trace.map((item, i) => (
            <TraceRow key={i} item={item} />
          ))}
        </div>
      )}

      {msg.finalText && (
        <div
          style={{
            background: "var(--bg-sunken)",
            borderRadius: "var(--radius-sm)",
            padding: "var(--space-3) var(--space-4)",
            fontFamily: "var(--font-serif)",
            fontSize: "var(--text-base)",
            lineHeight: "var(--leading-normal)",
            color: "var(--fg)",
            whiteSpace: "pre-wrap",
          }}
        >
          {msg.finalText}
        </div>
      )}

      {msg.running && msg.trace.length === 0 && (
        <p className="subtle" style={{ fontSize: "var(--text-sm)" }}>
          Thinking…
        </p>
      )}
    </div>
  );
}

function TraceRow({ item }: { item: TraceItem }) {
  if (item.kind === "tool") {
    const short = item.name.replace(/^mcp__geoforce__/, "");
    return (
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: "var(--space-3)",
          fontFamily: "var(--font-mono)",
          fontSize: "var(--text-xs)",
          color: "var(--fg-subtle)",
        }}
      >
        <span
          style={{
            background: "var(--bg-sunken)",
            color: "var(--accent-hover)",
            borderRadius: "var(--radius-sm)",
            padding: "2px 6px",
          }}
        >
          tool
        </span>
        <code>{short}</code>
        <TruncInput input={item.input} />
      </div>
    );
  }
  return (
    <p
      style={{
        margin: 0,
        color: "var(--fg)",
        fontSize: "var(--text-sm)",
        lineHeight: "var(--leading-normal)",
        whiteSpace: "pre-wrap",
      }}
    >
      {item.text}
    </p>
  );
}

function TruncInput({ input }: { input: Record<string, unknown> }) {
  let s = "";
  try {
    s = JSON.stringify(input);
  } catch {
    s = String(input);
  }
  if (s.length > 120) s = s.slice(0, 120) + "…";
  return (
    <span style={{ color: "var(--fg-subtle)", overflow: "hidden" }}>{s}</span>
  );
}
