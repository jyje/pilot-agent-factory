"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { API_BASE } from "@/lib/api";
import { splitReasoning } from "@/lib/reasoning";

export type RouteItem = { kind: "route"; next: string; reason: string };
export type TextItem = {
  kind: "text";
  role: "human" | "ai";
  content: string;
  agent?: string;
  reasoning?: string | null;
  streaming?: boolean;
};
export type ToolItem = {
  kind: "tool";
  name: string;
  args: Record<string, unknown>;
  output?: string;
};
export type NoticeItem = { kind: "notice"; detail: string };
export type TimelineItem = RouteItem | TextItem | ToolItem | NoticeItem;

export type ChatStatus = "ready" | "streaming" | "error";

type SseMessage = {
  role: string;
  name?: string | null;
  content: string;
  reasoning?: string | null;
  tool_calls: { name: string; args: Record<string, unknown> }[];
};

/** Parses the backend's SSE stream into a renderable timeline.
 *
 * `token` events accumulate into a live-streaming AI bubble (per agent);
 * the matching `message` event finalizes it — replacing the buffered text
 * with the cleaned content + extracted reasoning. Tool calls and their
 * results are paired into single ToolItems. */
export function useSupervisorChat() {
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [artifacts, setArtifacts] = useState<Record<string, Record<string, unknown>>>({});
  const [status, setStatus] = useState<ChatStatus>("ready");
  const [error, setError] = useState<string | null>(null);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  // set client-side only (crypto.randomUUID in a state initializer would
  // mismatch the server-prerendered HTML)
  const [sessionId, setSessionId] = useState<string>("");
  const abortRef = useRef<AbortController | null>(null);
  const lastPromptRef = useRef<string>("");

  useEffect(() => {
    setSessionId(crypto.randomUUID().slice(0, 8));
  }, []);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setActiveAgent(null);
    setStatus("ready");
  }, []);

  /** Abandon the server-side thread and start a fresh one. */
  const newSession = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setTimeline([]);
    setArtifacts({});
    setError(null);
    setActiveAgent(null);
    setStatus("ready");
    setSessionId(crypto.randomUUID().slice(0, 8));
  }, []);

  const handleEvent = useCallback((event: string, data: unknown) => {
    if (event === "token") {
      const { agent, text } = data as { agent: string; text: string };
      setActiveAgent(agent);
      setTimeline((t) => {
        const items = [...t];
        const last = items[items.length - 1];
        if (last?.kind === "text" && last.streaming && last.agent === agent) {
          items[items.length - 1] = { ...last, content: last.content + text };
        } else {
          // a different agent took over — settle the previous live bubble
          // (sub-agent bubbles never get a finalizing top-level message)
          if (last?.kind === "text" && last.streaming) {
            items[items.length - 1] = { ...last, ...splitReasoning(last.content), streaming: false };
          }
          items.push({ kind: "text", role: "ai", agent, content: text, streaming: true });
        }
        return items;
      });
    } else if (event === "done") {
      setTimeline((t) =>
        t.map((item) =>
          item.kind === "text" && item.streaming
            ? { ...item, ...splitReasoning(item.content), streaming: false }
            : item,
        ),
      );
    } else if (event === "route") {
      const { next, reason } = data as { next: string; reason: string };
      setTimeline((t) => [...t, { kind: "route", next, reason }]);
    } else if (event === "message") {
      const msg = data as SseMessage;
      setTimeline((t) => {
        const items = [...t];
        if (msg.role === "tool") {
          // attach the result to the last tool call still awaiting output
          for (let i = items.length - 1; i >= 0; i--) {
            const item = items[i];
            if (item.kind === "tool" && item.output === undefined) {
              items[i] = { ...item, output: msg.content };
              return items;
            }
          }
          return items;
        }
        // finalize the live bubble this message was streamed into
        let finalized = false;
        for (let i = items.length - 1; i >= 0; i--) {
          const item = items[i];
          if (item.kind === "text" && item.streaming) {
            items[i] =
              msg.content || msg.reasoning
                ? { ...item, content: msg.content, reasoning: msg.reasoning, streaming: false }
                : { ...item, streaming: false };
            finalized = true;
            break;
          }
        }
        if (!finalized && (msg.content || msg.reasoning)) {
          items.push({
            kind: "text",
            role: "ai",
            content: msg.content,
            reasoning: msg.reasoning,
          });
        }
        for (const tc of msg.tool_calls) {
          items.push({ kind: "tool", name: tc.name, args: tc.args });
        }
        return items;
      });
    } else if (event === "notice") {
      setTimeline((t) => [...t, { kind: "notice", detail: (data as { detail: string }).detail }]);
    } else if (event === "artifacts") {
      setArtifacts(data as Record<string, Record<string, unknown>>);
    } else if (event === "error") {
      setError((data as { detail: string }).detail);
      setStatus("error");
    }
  }, []);

  const send = useCallback(
    async (text: string) => {
      lastPromptRef.current = text;
      setTimeline((t) => [...t, { kind: "text", role: "human", content: text }]);
      setArtifacts({});
      setError(null);
      setStatus("streaming");
      const controller = new AbortController();
      abortRef.current = controller;
      try {
        const res = await fetch(`${API_BASE}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text, session_id: sessionId || "default" }),
          signal: controller.signal,
        });
        if (!res.ok || !res.body) throw new Error(`POST /api/chat failed: ${res.status}`);

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          let sep: number;
          while ((sep = buffer.indexOf("\n\n")) !== -1) {
            const frame = buffer.slice(0, sep);
            buffer = buffer.slice(sep + 2);
            let event = "message";
            let data = "";
            for (const line of frame.split("\n")) {
              if (line.startsWith("event: ")) event = line.slice(7).trim();
              else if (line.startsWith("data: ")) data += line.slice(6);
            }
            if (data) handleEvent(event, JSON.parse(data));
          }
        }
        setStatus((s) => (s === "error" ? s : "ready"));
      } catch (e) {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setError(e instanceof Error ? e.message : String(e));
        setStatus("error");
      } finally {
        abortRef.current = null;
        setActiveAgent(null);
      }
    },
    [handleEvent, sessionId],
  );

  /** Re-send the last prompt (used by the empty-reply notice). */
  const retry = useCallback(() => {
    if (lastPromptRef.current) void send(lastPromptRef.current);
  }, [send]);

  return {
    timeline,
    artifacts,
    status,
    error,
    activeAgent,
    send,
    stop,
    retry,
    sessionId,
    newSession,
  };
}
