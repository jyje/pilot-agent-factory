"use client";

import { useCallback, useRef, useState } from "react";

import { API_BASE } from "@/lib/api";

export type RouteItem = { kind: "route"; next: string; reason: string };
export type TextItem = { kind: "text"; role: "human" | "ai"; content: string };
export type ToolItem = {
  kind: "tool";
  name: string;
  args: Record<string, unknown>;
  output?: string;
};
export type TimelineItem = RouteItem | TextItem | ToolItem;

export type ChatStatus = "ready" | "streaming" | "error";

type SseMessage = {
  role: string;
  content: string;
  tool_calls: { name: string; args: Record<string, unknown> }[];
};

/** Parses the backend's SSE stream (route / message / artifacts / done / error)
 *  into a renderable timeline. AI tool calls and their tool results are paired
 *  into a single ToolItem so the UI can show input → output together. */
export function useSupervisorChat() {
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [artifacts, setArtifacts] = useState<Record<string, Record<string, unknown>>>({});
  const [status, setStatus] = useState<ChatStatus>("ready");
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setStatus("ready");
  }, []);

  const handleEvent = useCallback((event: string, data: unknown) => {
    if (event === "route") {
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
        for (const tc of msg.tool_calls) {
          items.push({ kind: "tool", name: tc.name, args: tc.args });
        }
        if (msg.content) {
          items.push({ kind: "text", role: "ai", content: msg.content });
        }
        return items;
      });
    } else if (event === "artifacts") {
      setArtifacts(data as Record<string, Record<string, unknown>>);
    } else if (event === "error") {
      setError((data as { detail: string }).detail);
      setStatus("error");
    }
  }, []);

  const send = useCallback(
    async (text: string) => {
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
          body: JSON.stringify({ message: text }),
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
      }
    },
    [handleEvent],
  );

  return { timeline, artifacts, status, error, send, stop };
}
