import { create } from "zustand";
import {
  createSession,
  deleteSession,
  predictFields,
  predictFieldsInline,
  streamSessionQuery,
} from "./api/client";
import type { AgentEvent, PredictResponse, Scenario } from "./api/client";

export type TraceItem =
  | { kind: "text"; text: string }
  | { kind: "tool"; name: string; input: Record<string, unknown> };

/** One turn in the chat. `user` bubbles are authored by the engineer;
 *  `agent` bubbles accumulate streamed text + tool-use chips. */
export type ChatMessage =
  | { id: string; role: "user"; text: string }
  | {
      id: string;
      role: "agent";
      trace: TraceItem[];
      finalText: string;
      stopReason: string | null;
      running: boolean;
    };

type State = {
  scenarios: Scenario[];
  selectedId: string | null;
  query: string;
  error: string | null;

  // Hero canvas (scenario preview) — unchanged.
  fields: PredictResponse | null;
  fieldsLoading: boolean;
  fieldsError: string | null;

  // Canvas driven by agent tool calls during a chat turn. Wins over `fields`.
  agentFields: PredictResponse | null;
  agentFieldsBusy: boolean;

  // Chat state.
  sessionId: string | null;
  sessionStarting: boolean;
  messages: ChatMessage[];
  sending: boolean;

  setScenarios: (s: Scenario[]) => void;
  selectScenario: (id: string) => void;
  setQuery: (q: string) => void;
  setError: (msg: string | null) => void;
  loadFields: (scenarioId: string) => Promise<void>;

  ensureSession: () => Promise<string>;
  sendMessage: (text: string, scenarioId?: string | null) => Promise<void>;
  resetChat: () => Promise<void>;
};

/** Light unique id — good enough for React keys. */
function uid(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export const useStore = create<State>((set, get) => ({
  scenarios: [],
  selectedId: null,
  query: "",
  error: null,

  fields: null,
  fieldsLoading: false,
  fieldsError: null,

  agentFields: null,
  agentFieldsBusy: false,

  sessionId: null,
  sessionStarting: false,
  messages: [],
  sending: false,

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

  ensureSession: async () => {
    const cur = get().sessionId;
    if (cur) return cur;
    set({ sessionStarting: true, error: null });
    try {
      const sid = await createSession();
      set({ sessionId: sid, sessionStarting: false });
      return sid;
    } catch (err) {
      set({
        sessionStarting: false,
        error: err instanceof Error ? err.message : String(err),
      });
      throw err;
    }
  },

  resetChat: async () => {
    const sid = get().sessionId;
    set({ messages: [], agentFields: null, error: null, sessionId: null });
    if (sid) {
      // Background fire-and-forget — don't block the UI waiting for close.
      void deleteSession(sid);
    }
  },

  sendMessage: async (text, scenarioId) => {
    if (!text.trim() || get().sending) return;

    // Clear agent-driven canvas at the start of every new turn so we don't
    // stale-show a previous turn's fields while the new one is still calling
    // tools. Scenario preview (`fields`) stays intact.
    const userMsg: ChatMessage = { id: uid("u"), role: "user", text };
    const agentId = uid("a");
    const agentMsg: ChatMessage = {
      id: agentId,
      role: "agent",
      trace: [],
      finalText: "",
      stopReason: null,
      running: true,
    };
    set({
      sending: true,
      error: null,
      agentFields: null,
      messages: [...get().messages, userMsg, agentMsg],
    });

    const updateAgent = (patch: (m: Extract<ChatMessage, { role: "agent" }>) => void) => {
      set({
        messages: get().messages.map((m) => {
          if (m.id !== agentId || m.role !== "agent") return m;
          const next = { ...m };
          patch(next);
          return next;
        }),
      });
    };

    const onEvent = (e: AgentEvent) => {
      if (e.type === "text") {
        updateAgent((m) => {
          const last = m.trace[m.trace.length - 1];
          if (last && last.kind === "text") {
            m.trace = [...m.trace];
            m.trace[m.trace.length - 1] = {
              kind: "text",
              text: last.text + e.text,
            };
          } else {
            m.trace = [...m.trace, { kind: "text", text: e.text }];
          }
        });
      } else if (e.type === "tool") {
        updateAgent((m) => {
          m.trace = [
            ...m.trace,
            { kind: "tool", name: e.name, input: e.input },
          ];
        });
        const engine =
          e.name === "mcp__geoforce__predict_solver"
            ? "solver"
            : e.name === "mcp__geoforce__predict_surrogate"
              ? "surrogate"
              : null;
        const scenario = e.input?.scenario as
          | Record<string, unknown>
          | undefined;
        if (engine && scenario) {
          set({ agentFieldsBusy: true });
          predictFieldsInline(scenario, engine)
            .then((res) => {
              const prev = get().agentFields;
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
        updateAgent((m) => {
          m.finalText = e.final_text;
          m.stopReason = e.stop_reason;
        });
      } else if (e.type === "error") {
        set({ error: e.message });
      }
    };

    try {
      const sid = await get().ensureSession();
      await streamSessionQuery(
        sid,
        { query: text, scenario_id: scenarioId ?? undefined },
        onEvent,
      );
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) });
    } finally {
      updateAgent((m) => {
        m.running = false;
      });
      set({ sending: false });
    }
  },
}));
