import { useEffect } from "react";
import { useStore } from "../store";
import { FieldPlot } from "./FieldPlot";

export function FieldPanel() {
  const selectedId = useStore((s) => s.selectedId);
  const scenarioFields = useStore((s) => s.fields);
  const loading = useStore((s) => s.fieldsLoading);
  const error = useStore((s) => s.fieldsError);
  const loadFields = useStore((s) => s.loadFields);
  const agentFields = useStore((s) => s.agentFields);
  const agentBusy = useStore((s) => s.agentFieldsBusy);

  useEffect(() => {
    if (selectedId) loadFields(selectedId);
  }, [selectedId, loadFields]);

  // Agent output wins once the agent has produced at least one field.
  const fields = agentFields ?? scenarioFields;
  const source: "agent" | "scenario" = agentFields ? "agent" : "scenario";

  if (!selectedId && !agentFields) return null;

  if (loading && !agentFields) {
    return (
      <div className="card">
        <span className="label">Fields</span>
        <p className="muted" style={{ marginTop: "var(--space-2)" }}>
          Running solver and surrogate…
        </p>
      </div>
    );
  }

  if (error && !agentFields) {
    return (
      <div className="card">
        <span className="label">Fields</span>
        <p className="muted" style={{ marginTop: "var(--space-2)" }}>
          Could not load fields: {error}
        </p>
      </div>
    );
  }

  if (!fields || (!fields.solver && !fields.surrogate)) return null;

  // Shared color range across whichever engines are present.
  const tmins = [fields.solver?.t_min, fields.surrogate?.t_min].filter(
    (v): v is number => typeof v === "number",
  );
  const tmaxs = [fields.solver?.t_max, fields.surrogate?.t_max].filter(
    (v): v is number => typeof v === "number",
  );
  const tMin = Math.min(...tmins);
  const tMax = Math.max(...tmaxs);
  const tDelta =
    fields.solver && fields.surrogate
      ? Math.abs(fields.solver.t_max - fields.surrogate.t_max)
      : null;

  return (
    <div
      style={{
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
          gap: "var(--space-3)",
        }}
      >
        <span className="label">Temperature fields</span>
        <div style={{ display: "flex", gap: "var(--space-2)" }}>
          <span
            className="chip"
            title={
              source === "agent"
                ? "Rendered from the agent's own tool calls during this query."
                : "Preview from the selected scenario card."
            }
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "var(--text-xs)",
              borderColor:
                source === "agent" ? "var(--accent)" : "var(--border-subtle)",
              color: source === "agent" ? "var(--accent-hover)" : undefined,
            }}
          >
            {source === "agent"
              ? agentBusy
                ? "from agent · updating…"
                : "from agent"
              : "from scenario"}
          </span>
          {tDelta !== null && (
            <span
              className="chip"
              title="Peak-temperature gap between the two engines"
              style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)" }}
            >
              Δ Tmax {tDelta.toFixed(1)}°C
            </span>
          )}
        </div>
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns:
            fields.solver && fields.surrogate ? "1fr 1fr" : "1fr",
          gap: "var(--space-4)",
        }}
      >
        {fields.solver && (
          <FieldPlot
            title="GeoForce-Solver"
            result={fields.solver}
            tMin={tMin}
            tMax={tMax}
          />
        )}
        {fields.surrogate && (
          <FieldPlot
            title="ReservoirCNN v1.1"
            result={fields.surrogate}
            tMin={tMin}
            tMax={tMax}
          />
        )}
      </div>
    </div>
  );
}
