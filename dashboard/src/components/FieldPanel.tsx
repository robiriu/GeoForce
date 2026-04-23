import { useEffect } from "react";
import { useStore } from "../store";
import { FieldPlot } from "./FieldPlot";

export function FieldPanel() {
  const selectedId = useStore((s) => s.selectedId);
  const fields = useStore((s) => s.fields);
  const loading = useStore((s) => s.fieldsLoading);
  const error = useStore((s) => s.fieldsError);
  const loadFields = useStore((s) => s.loadFields);

  useEffect(() => {
    if (selectedId) loadFields(selectedId);
  }, [selectedId, loadFields]);

  if (!selectedId) return null;

  if (loading) {
    return (
      <div className="card">
        <span className="label">Fields</span>
        <p className="muted" style={{ marginTop: "var(--space-2)" }}>
          Running solver and surrogate…
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <span className="label">Fields</span>
        <p className="muted" style={{ marginTop: "var(--space-2)" }}>
          Could not load fields: {error}
        </p>
      </div>
    );
  }

  if (!fields || !fields.solver || !fields.surrogate) return null;

  // Shared color range so the two heatmaps are directly comparable.
  const tMin = Math.min(fields.solver.t_min, fields.surrogate.t_min);
  const tMax = Math.max(fields.solver.t_max, fields.surrogate.t_max);
  const tDelta = Math.abs(fields.solver.t_max - fields.surrogate.t_max);

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
        }}
      >
        <span className="label">Temperature fields</span>
        <span
          className="chip"
          title="Peak-temperature gap between the two engines"
          style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)" }}
        >
          Δ Tmax {tDelta.toFixed(1)}°C
        </span>
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "var(--space-4)",
        }}
      >
        <FieldPlot
          title="GeoForce-Solver"
          result={fields.solver}
          tMin={tMin}
          tMax={tMax}
        />
        <FieldPlot
          title="ReservoirCNN v1.1"
          result={fields.surrogate}
          tMin={tMin}
          tMax={tMax}
        />
      </div>
    </div>
  );
}
