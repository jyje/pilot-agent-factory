"use client";

import {
  Message,
  MessageContent,
  MessageResponse,
} from "@/components/ai-elements/message";
import {
  Reasoning,
  ReasoningContent,
  ReasoningTrigger,
} from "@/components/ai-elements/reasoning";
import { Badge } from "@/components/ui/badge";
import type { TextItem } from "@/hooks/use-supervisor-chat";
import { splitStreamingReasoning } from "@/lib/reasoning";

/** Custom wrapper: one chat bubble.
 *
 * Sub-agent bubbles carry a badge naming who produced the text; the
 * supervisor is the conversation's default speaker, so its bubbles stay
 * unlabeled. Model thinking lives in the AI Elements Reasoning fold: it
 * streams open while tokens arrive and auto-collapses ("Thought for N
 * seconds") once the stream ends. */
export function ChatMessage({ item }: { item: TextItem }) {
  if (item.role === "human") {
    return (
      <Message from="user">
        <MessageContent>
          <MessageResponse>{item.content}</MessageResponse>
        </MessageContent>
      </Message>
    );
  }

  // live tokens: thinking is detected on the fly; finalized: the backend /
  // client splitter already separated reasoning from the answer
  const view = item.streaming
    ? splitStreamingReasoning(item.content)
    : { reasoning: item.reasoning ?? null, content: item.content };

  const agent = item.agent ?? "supervisor";
  const showBadge = agent !== "supervisor";
  return (
    <div className="space-y-1">
      {(showBadge || item.streaming) && (
        <div className="flex items-center gap-2">
          {showBadge && (
            <Badge variant="default" className="text-xs">
              {agent}
            </Badge>
          )}
          {item.streaming && (
            <span className="size-2 animate-pulse rounded-full bg-primary" />
          )}
        </div>
      )}
      {view.reasoning && (
        <Reasoning isStreaming={!!item.streaming}>
          <ReasoningTrigger />
          <ReasoningContent>{view.reasoning}</ReasoningContent>
        </Reasoning>
      )}
      {view.content && (
        <Message from="assistant">
          <MessageContent>
            <MessageResponse>{view.content}</MessageResponse>
          </MessageContent>
        </Message>
      )}
    </div>
  );
}
