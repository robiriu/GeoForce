import { create } from "zustand";
import { predictFields, predictFieldsInline } from "./api/client";
import type { AgentEvent, PredictResponse, Scenario } from "./api/client";

export type TraceItem =
  | { kind: "text"; text: string }
  | { kind: "tool"; name: string; input: Record<string, unknown> };

type State = {
  scenarios: Scenario[];
  selectedId: string | null;
  query: string;
  trace: TraceItem[];
  finalText: string;
  stopReason: string | null;
  running: boolean;
  error: string | null;

  fields: PredictResponse | null;
  fieldsLoading: boolean;
  fieldsError: string | null;

  /** Fields derived from the agent's own tool calls during a /query run.
   * When present, the FieldPanel renders these instead of the scenario
   * preview — so "Ask agent" actually shows what the agent computed. */
  agentFields: PredictResponse | null;
  agentFieldsBusy: boolean;

  setScenarios: (s: Scenario[]) => void;
  selectScenario: (id: string) => void;
  setQuery: (q: string) => void;
  beginRun: () => void;
  pushEvent: (e: AgentEvent) => void;
  endRun: () => void;
  setError: (msg: string | null) => void;
  loadFields: (scenarioId: string) => Promise<void>;
};

export const useStore = create<State>((set, get) => ({
  scenarios: [],
  selectedId: null,
  query: "",
  trace: [],
  finalText: "",
  stopReason: null,
  running: false,
  error: null,

  fields: null,
  fieldsLoading: false,
  fieldsError: null,

  agentFields: null,
  agentFieldsBusy: false,

  setScenarios: (s) => {
    const first = s[0]?.id ?? null;
    set({
      scenarios: s,
      selectedId: get().selectedId ?? first,
      query: get().query || (s[0]?.question ?? ""),
    });
  },
  selectScenario: (id) => {
    const match = get().scenarios.find((s) => s.id === id);
    set({ selectedId: id, query: match?.question ?? get().query });
  },
  setQuery: (q) => set({ query: q }),

  beginRun: () =>
    set({
      running: true,
      trace: [],
      finalText: "",
      stopReason: null,
      error: null,
      agentFields: null,
    }),

  pushEvent: (e) => {
    const s = get();
    if (e.type === "text") {
      // Coalesce adjacent text chunks into a single trace item
      const last = s.trace[s.trace.length - 1];
      if (last && last.kind === "text") {
        const updated = [...s.trace];
        updated[updated.length - 1] = { kind: "text", text: last.text + e.text };
        set({ trace: updated });
      } else {
        set({ trace: [...s.trace, { kind: "text", text: e.text }] });
      }
    } else if (e.type === "tool") {
      set({ trace: [...s.trace, { kind: "tool", name: e.name, input: e.input }] });
      // If the agent called a predict_* tool, re-run the same scenario
      // through /predict so the canvas can show the field it reasoned about.
      const engine =
        e.name === "mcp__geoforce__predict_solver"
          ? "solver"
          : e.name === "mcp__geoforce__predict_surrogate"
            ? "surrogate"
            : null;
      const scenario = e.input?.scenario as Record<string, unknown> | undefined;
      if (engine && scenario) {
        set({ agentFieldsBusy: true });
        predictFieldsInline(scenario, engine)
          .then((res) => {
            const prev = get().agentFields;
            // Merge so a sequence of solver→surrogate calls shows both.
            const merged: PredictResponse = {
              engine: "both",
              solver: engine === "solver" ? res.solver : prev?.solver,
              surrogate:
                engine === "surrogate" ? res.surrogate : prev?.surrogate,
            };
            set({ agentFields: merged, agentFieldsBusy: false });
          })
          .catch(() => set({ agentFieldsBusy: false }));
      }
    } else if (e.type === "result") {
      set({ finalText: e.final_text, stopReason: e.stop_reason });
    } else if (e.type === "error") {
      set({ error: e.message });
    }
  },

  endRun: () => set({ running: false }),
  setError: (msg) => set({ error: msg }),

  loadFields: async (scenarioId) => {
    set({ fieldsLoading: true, fieldsError: null });
    try {
      const res = await predictFields(scenarioId, "both");
      set({ fields: res, fieldsLoading: false });
    } catch (err) {
      set({
        fields: null,
        fieldsLoading: false,
        fieldsError: err instanceof Error ? err.message : String(err),
      });
    }
  },
}));
