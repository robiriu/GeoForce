import { useEffect, useRef } from "react";
import { magma } from "../viz/magma";

type FieldResult = {
  grid: { nx: number; ny: number; dx: number; dy: number };
  temperature: number[][];
  pressure: number[][];
  t_min: number;
  t_max: number;
  p_min_MPa: number;
  p_max_MPa: number;
  elapsed_seconds: number;
};

export function FieldPlot({
  title,
  result,
  tMin,
  tMax,
}: {
  title: string;
  result: FieldResult;
  tMin: number;
  tMax: number;
}) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const nx = result.grid.nx;
    const ny = result.grid.ny;
    canvas.width = nx;
    canvas.height = ny;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const img = ctx.createImageData(nx, ny);
    const range = tMax - tMin || 1;
    for (let j = 0; j < ny; j++) {
      const jSrc = ny - 1 - j; // flip so origin=bottom-left
      for (let i = 0; i < nx; i++) {
        const v = result.temperature[i]?.[jSrc] ?? tMin;
        const [r, g, b] = magma((v - tMin) / range);
        const idx = (j * nx + i) * 4;
        img.data[idx] = r;
        img.data[idx + 1] = g;
        img.data[idx + 2] = b;
        img.data[idx + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
  }, [result, tMin, tMax]);

  const extentX = result.grid.nx * result.grid.dx;
  const extentY = result.grid.ny * result.grid.dy;

  return (
    <div
      style={{
        background: "var(--bg-elevated)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
        padding: "var(--space-4)",
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-2)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <h3
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: "var(--text-lg)",
            margin: 0,
          }}
        >
          {title}
        </h3>
        <span className="subtle" style={{ fontSize: "var(--text-xs)" }}>
          {result.elapsed_seconds.toFixed(2)} s
        </span>
      </div>
      <canvas
        ref={ref}
        style={{
          width: "100%",
          aspectRatio: "1 / 1",
          imageRendering: "pixelated",
          borderRadius: "var(--radius-sm)",
          background: "var(--bg-sunken)",
        }}
      />
      <Colorbar tMin={tMin} tMax={tMax} />
      <p
        className="muted"
        style={{
          fontFamily: "var(--font-serif)",
          fontStyle: "italic",
          fontSize: "var(--text-sm)",
        }}
      >
        T {result.t_min.toFixed(1)}–{result.t_max.toFixed(1)}°C &middot; P{" "}
        {result.p_min_MPa.toFixed(2)}–{result.p_max_MPa.toFixed(2)} MPa &middot; extent{" "}
        {(extentX / 1000).toFixed(1)}×{(extentY / 1000).toFixed(1)} km
      </p>
    </div>
  );
}

function Colorbar({ tMin, tMax }: { tMin: number; tMax: number }) {
  const stops = Array.from({ length: 32 }, (_, i) => i / 31);
  return (
    <div>
      <div
        style={{
          display: "flex",
          height: 8,
          borderRadius: "var(--radius-sm)",
          overflow: "hidden",
        }}
      >
        {stops.map((t, i) => {
          const [r, g, b] = magma(t);
          return (
            <div
              key={i}
              style={{
                flex: 1,
                background: `rgb(${r}, ${g}, ${b})`,
              }}
            />
          );
        })}
      </div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: "var(--text-xs)",
          color: "var(--fg-subtle)",
          marginTop: 2,
          fontFamily: "var(--font-mono)",
        }}
      >
        <span>{tMin.toFixed(0)}°C</span>
        <span>{tMax.toFixed(0)}°C</span>
      </div>
    </div>
  );
}
