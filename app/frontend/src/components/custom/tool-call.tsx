"use client";

import { useEffect, useRef, useState } from "react";

import { Shimmer } from "@/components/ai-elements/shimmer";
import {
  Tool,
  ToolContent,
  ToolHeader,
  ToolInput,
  ToolOutput,
} from "@/components/ai-elements/tool";
import type { ToolItem } from "@/hooks/use-supervisor-chat";
import { ChatMessage } from "./chat-message";

/** Custom wrapper: a delegation card on the AI Elements Tool shape.
 *
 * For deep-mode `task` calls the card is a container for the whole
 * delegation, keeping the transcript chronological: parameters → the
 * sub-agent's live bubbles (nested `children`) → result. Like the Reasoning
 * fold, it stays open while the sub-agent works and auto-collapses once the
 * result lands. */
export function ToolCall({ item }: { item: ToolItem }) {
  const running = item.output === undefined;
  const [open, setOpen] = useState(running);
  const wasRunning = useRef(running);
  useEffect(() => {
    if (wasRunning.current && !running) setOpen(false);
    wasRunning.current = running;
  }, [running]);

  // the `task` tool is really an agent delegation — label it as such:
  // "agent → calculator"; the label shimmers while the delegation runs
  const target = typeof item.args.subagent_type === "string" ? item.args.subagent_type : null;
  const label =
    item.name === "task" ? `agent${target ? ` → ${target}` : ""}` : item.name;
  return (
    <Tool open={open} onOpenChange={setOpen}>
      <ToolHeader
        type={`tool-${item.name}`}
        title={
          running ? (
            <Shimmer as="span" duration={1.5} className="font-medium text-sm">
              {label}
            </Shimmer>
          ) : (
            label
          )
        }
        state={running ? "input-available" : "output-available"}
      />
      <ToolContent>
        <ToolInput input={item.args} />
        {item.children && item.children.length > 0 && (
          <div className="space-y-2">
            <h4 className="font-medium text-muted-foreground text-xs uppercase tracking-wide">
              Delegated work
            </h4>
            <div className="space-y-2 border-muted border-l-2 pl-3">
              {item.children.map((child, i) => (
                <ChatMessage key={i} item={child} />
              ))}
            </div>
          </div>
        )}
        {item.output !== undefined && (
          <ToolOutput errorText={undefined} output={item.output} />
        )}
      </ToolContent>
    </Tool>
  );
}
