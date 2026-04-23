import { create } from "zustand";
import type { AgentEvent, Scenario } from "./api/client";

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

  setScenarios: (s: Scenario[]) => void;
  selectScenario: (id: string) => void;
  setQuery: (q: string) => void;
  beginRun: () => void;
  pushEvent: (e: AgentEvent) => void;
  endRun: () => void;
  setError: (msg: string | null) => void;
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
    } else if (e.type === "result") {
      set({ finalText: e.final_text, stopReason: e.stop_reason });
    } else if (e.type === "error") {
      set({ error: e.message });
    }
  },

  endRun: () => set({ running: false }),
  setError: (msg) => set({ error: msg }),
}));
