export function Header({ healthy }: { healthy: boolean | null }) {
  return (
    <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <div>
        <h1 style={{ fontSize: "var(--text-2xl)", letterSpacing: "-0.02em", fontWeight: 700 }}>
          <span style={{ color: "var(--accent)" }}>Geo</span>Force
          <span style={{ fontSize: "var(--text-sm)", fontWeight: 500, color: "var(--fg-subtle)", marginLeft: "var(--space-2)" }}>
            v2.0
          </span>
        </h1>
        <p className="muted" style={{ fontSize: "var(--text-sm)", marginTop: "var(--space-1)" }}>
          Dual-engine geothermal platform — numerical solver + CNN surrogate with AI agent orchestration
        </p>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            padding: "4px 12px",
            fontSize: "var(--text-xs)",
            fontWeight: 500,
            borderRadius: "var(--radius-pill)",
            background: healthy
              ? "rgba(34, 197, 94, 0.1)"
              : healthy === false
                ? "rgba(239, 68, 68, 0.1)"
                : "rgba(255, 255, 255, 0.05)",
            color: healthy
              ? "var(--success)"
              : healthy === false
                ? "var(--danger)"
                : "var(--fg-subtle)",
            border: `1px solid ${
              healthy
                ? "rgba(34, 197, 94, 0.2)"
                : healthy === false
                  ? "rgba(239, 68, 68, 0.2)"
                  : "var(--border-subtle)"
            }`,
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: healthy
                ? "var(--success)"
                : healthy === false
                  ? "var(--danger)"
                  : "var(--fg-subtle)",
            }}
          />
          {healthy === null ? "Connecting" : healthy ? "Online" : "Offline"}
        </span>
        <span
          style={{
            fontSize: "var(--text-xs)",
            color: "var(--fg-subtle)",
            fontWeight: 500,
          }}
        >
          ForceX AI
        </span>
      </div>
    </header>
  );
}
