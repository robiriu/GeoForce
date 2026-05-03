export function Header({ healthy }: { healthy: boolean | null }) {
  return (
    <header style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
      <div>
        <h1 style={{ fontSize: "var(--text-3xl)", letterSpacing: "-0.01em" }}>
          GeoForce
        </h1>
        <p className="muted" style={{ fontSize: "var(--text-base)", marginTop: "var(--space-2)" }}>
          AI-orchestrated open-source geothermal solver and physics-informed CNN surrogate
          for Indonesian reservoirs.
        </p>
      </div>
      <div style={{ textAlign: "right" }}>
        <span className="chip">
          {healthy === null ? "checking…" : healthy ? "backend online" : "backend offline"}
        </span>
      </div>
    </header>
  );
}
