"use client";

import { useEffect, useState } from "react";
import { FactoryIcon } from "lucide-react";

import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import {
  Message,
  MessageContent,
  MessageResponse,
} from "@/components/ai-elements/message";
import {
  PromptInput,
  PromptInputBody,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
  type PromptInputMessage,
} from "@/components/ai-elements/prompt-input";
import { AgentCard, LoadErrorCard } from "@/components/custom/agent-card";
import { ArtifactsCard } from "@/components/custom/artifacts-card";
import { RouteStep } from "@/components/custom/route-step";
import { ToolCall } from "@/components/custom/tool-call";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { useSupervisorChat } from "@/hooks/use-supervisor-chat";
import { fetchAgents, type AgentsResponse } from "@/lib/api";

export default function Home() {
  const [agents, setAgents] = useState<AgentsResponse | null>(null);
  const [agentsError, setAgentsError] = useState<string | null>(null);
  const { timeline, artifacts, status, error, send, stop } = useSupervisorChat();

  useEffect(() => {
    fetchAgents().then(setAgents).catch((e) => setAgentsError(String(e)));
  }, []);

  const handleSubmit = (message: PromptInputMessage) => {
    const text = message.text?.trim();
    if (!text || status === "streaming") return;
    void send(text);
  };

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center gap-2 border-b px-4 py-3">
        <FactoryIcon className="size-5" />
        <h1 className="font-semibold text-sm">Agent Factory</h1>
        <span className="text-muted-foreground text-xs">
          supervisor over runtime-loaded sub-agents
        </span>
      </header>

      <div className="flex min-h-0 flex-1">
        <aside className="w-72 shrink-0 border-r">
          <ScrollArea className="h-full">
            <div className="space-y-2 p-3">
              <p className="font-medium text-muted-foreground text-xs uppercase">
                Loaded agents {agents ? `(${agents.agents.length})` : ""}
              </p>
              {agentsError && (
                <p className="text-destructive text-xs">
                  backend unreachable: {agentsError}
                </p>
              )}
              {agents?.agents.map((m) => (
                <AgentCard key={m.name} manifest={m} />
              ))}
              {agents && agents.errors.length > 0 && (
                <>
                  <Separator />
                  <p className="font-medium text-muted-foreground text-xs uppercase">
                    Load failures ({agents.errors.length})
                  </p>
                  {agents.errors.map((e) => (
                    <LoadErrorCard key={e.source} error={e} />
                  ))}
                </>
              )}
            </div>
          </ScrollArea>
        </aside>

        <main className="flex min-w-0 flex-1 flex-col">
          <Conversation className="min-h-0 flex-1">
            <ConversationContent className="mx-auto w-full max-w-3xl">
              {timeline.length === 0 && (
                <ConversationEmptyState
                  title="Ask the supervisor"
                  description='Try "What is (17 + 25) * 3?" — the router will pick an agent.'
                />
              )}
              {timeline.map((item, i) => {
                if (item.kind === "route") return <RouteStep key={i} decision={item} />;
                if (item.kind === "tool") return <ToolCall key={i} item={item} />;
                return (
                  <Message key={i} from={item.role === "human" ? "user" : "assistant"}>
                    <MessageContent>
                      <MessageResponse>{item.content}</MessageResponse>
                    </MessageContent>
                  </Message>
                );
              })}
              <ArtifactsCard artifacts={artifacts} />
              {error && <p className="text-destructive text-xs">{error}</p>}
            </ConversationContent>
            <ConversationScrollButton />
          </Conversation>

          <div className="mx-auto w-full max-w-3xl p-3">
            <PromptInput onSubmit={handleSubmit}>
              <PromptInputBody>
                <PromptInputTextarea placeholder="Ask anything — the supervisor routes it" />
              </PromptInputBody>
              <PromptInputFooter>
                <span />
                <PromptInputSubmit
                  onStop={stop}
                  status={status === "streaming" ? "streaming" : "ready"}
                />
              </PromptInputFooter>
            </PromptInput>
          </div>
        </main>
      </div>
    </div>
  );
}
