/**
 * SSE client for the GeoForce FastAPI backend.
 *
 * Uses fetch + ReadableStream to consume Server-Sent Events from POST /query.
 * (Native EventSource only supports GET, so we parse SSE manually.)
 */

export type Scenario = {
  id: string;
  question: string;
  scenario: Record<string, unknown>;
  [k: string]: unknown;
};

export type AgentEvent =
  | { type: "text"; text: string }
  | { type: "tool"; name: string; input: Record<string, unknown> }
  | { type: "result"; final_text: string; stop_reason: string | null }
  | { type: "error"; message: string };

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export type FieldResult = {
  grid: { nx: number; ny: number; dx: number; dy: number };
  temperature: number[][];
  pressure: number[][];
  t_min: number;
  t_max: number;
  p_min_MPa: number;
  p_max_MPa: number;
  elapsed_seconds: number;
};

export type PredictResponse = {
  engine: "both" | "solver" | "surrogate";
  solver?: FieldResult;
  surrogate?: FieldResult;
};

export async function predictFields(
  scenario_id: string,
  engine: "both" | "solver" | "surrogate" = "both",
): Promise<PredictResponse> {
  const res = await fetch(`${API_BASE}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario_id, engine }),
  });
  if (!res.ok) throw new Error(`predict: ${res.status}`);
  return res.json();
}

/** Run /predict with an inline scenario dict (what the agent passes to its
 * predict_solver / predict_surrogate tools). Returns fields for the dashboard
 * canvas; runs locally on the backend, no extra API tokens consumed. */
export async function predictFieldsInline(
  scenario: Record<string, unknown>,
  engine: "solver" | "surrogate",
): Promise<PredictResponse> {
  const res = await fetch(`${API_BASE}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario, engine }),
  });
  if (!res.ok) throw new Error(`predict: ${res.status}`);
  return res.json();
}

export async function fetchScenarios(): Promise<Scenario[]> {
  const res = await fetch(`${API_BASE}/scenarios`);
  if (!res.ok) throw new Error(`scenarios: ${res.status}`);
  const data = await res.json();
  return (data?.scenarios ?? []) as Scenario[];
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`);
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * POST /query and stream SSE events (single-shot, no session).
 * Calls onEvent for each parsed event; resolves when the stream ends.
 */
export async function streamQuery(
  body: { query: string; scenario_id?: string },
  onEvent: (e: AgentEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  await _streamSSE(`${API_BASE}/query`, body, onEvent, signal);
}

/** Open a multi-turn session. The returned id is used by streamSessionQuery. */
export async function createSession(): Promise<string> {
  const res = await fetch(`${API_BASE}/sessions`, { method: "POST" });
  if (!res.ok) throw new Error(`sessions: ${res.status}`);
  const data = (await res.json()) as { session_id: string };
  return data.session_id;
}

export async function deleteSession(sessionId: string): Promise<void> {
  try {
    await fetch(`${API_BASE}/sessions/${sessionId}`, { method: "DELETE" });
  } catch {
    /* best-effort */
  }
}

/** Stream one turn against an existing session — the model sees prior turns. */
export async function streamSessionQuery(
  sessionId: string,
  body: { query: string; scenario_id?: string },
  onEvent: (e: AgentEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  await _streamSSE(
    `${API_BASE}/sessions/${sessionId}/query`,
    body,
    onEvent,
    signal,
  );
}

async function _streamSSE(
  url: string,
  body: Record<string, unknown>,
  onEvent: (e: AgentEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`sse: ${res.status}`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split(/\r?\n\r?\n/);
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      if (!chunk.trim()) continue;
      const parsed = parseSSEChunk(chunk);
      if (parsed) onEvent(parsed);
    }
  }
}

function parseSSEChunk(chunk: string): AgentEvent | null {
  let eventName = "message";
  const dataLines: string[] = [];
  for (const line of chunk.split(/\r?\n/)) {
    if (line.startsWith("event:")) {
      eventName = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }
  if (dataLines.length === 0) return null;
  const dataStr = dataLines.join("\n");
  let payload: Record<string, unknown> = {};
  try {
    payload = JSON.parse(dataStr);
  } catch {
    return null;
  }
  switch (eventName) {
    case "text":
      return { type: "text", text: String(payload.text ?? "") };
    case "tool":
      return {
        type: "tool",
        name: String(payload.name ?? "unknown"),
        input: (payload.input as Record<string, unknown>) ?? {},
      };
    case "result":
      return {
        type: "result",
        final_text: String(payload.final_text ?? ""),
        stop_reason: (payload.stop_reason as string | null) ?? null,
      };
    case "error":
      return { type: "error", message: String(payload.message ?? "unknown error") };
    default:
      return null;
  }
}
