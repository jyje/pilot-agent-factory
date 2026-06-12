"use client";

import { useEffect, useState } from "react";
import { FactoryIcon, NetworkIcon, RotateCcwIcon } from "lucide-react";

import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import {
  PromptInputSubmit,
  PromptInputTextarea,
} from "@/components/ai-elements/prompt-input";
import { ActiveAgentIndicator } from "@/components/custom/active-agent";
import { AgentCard, LoadErrorCard } from "@/components/custom/agent-card";
import { ArtifactsCard } from "@/components/custom/artifacts-card";
import { ChatMessage } from "@/components/custom/chat-message";
import { GraphDialog } from "@/components/custom/graph-view";
import { NoticeCard } from "@/components/custom/notice-card";
import { RouteStep } from "@/components/custom/route-step";
import { ThinkingShimmer } from "@/components/custom/thinking-shimmer";
import { ToolCall } from "@/components/custom/tool-call";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { useSupervisorChat } from "@/hooks/use-supervisor-chat";
import { fetchAgents, type AgentsResponse } from "@/lib/api";

export default function Home() {
  const [agents, setAgents] = useState<AgentsResponse | null>(null);
  const [agentsError, setAgentsError] = useState<string | null>(null);
  const [graphScope, setGraphScope] = useState<string | null>(null);
  const {
    timeline,
    artifacts,
    status,
    error,
    activeAgent,
    thinking,
    send,
    stop,
    retry,
    sessionId,
    newSession,
  } = useSupervisorChat();

  useEffect(() => {
    fetchAgents().then(setAgents).catch((e) => setAgentsError(String(e)));
  }, []);

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const text = (formData.get("prompt") as string)?.trim();
    if (!text || status === "streaming") return;

    void send(text);
    e.currentTarget.reset();
  };

  return (
    <div className="flex h-screen flex-col bg-background">
      {/* Header */}
      <header className="shrink-0 border-b border-border/40">
        <div className="flex items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-2">
            <FactoryIcon className="size-5" />
            <div>
              <h1 className="font-semibold text-sm">Agent Factory</h1>
              <p className="text-muted-foreground text-xs">
                deep supervisor with runtime-loaded agents
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="font-mono text-xs">
              {sessionId ? `session ${sessionId.slice(0, 8)}…` : "no session"}
            </Badge>
            <Button size="sm" variant="ghost" onClick={newSession} title="Start new conversation">
              <RotateCcwIcon className="size-4" />
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setGraphScope("")} title="View platform structure">
              <NetworkIcon className="size-4" />
            </Button>
          </div>
        </div>
      </header>

      <GraphDialog scope={graphScope} onClose={() => setGraphScope(null)} />

      {/* Main layout */}
      <div className="flex min-h-0 flex-1">
        {/* Sidebar — agents list */}
        <aside className="w-64 shrink-0 border-r border-border/40">
          <ScrollArea className="h-full">
            <div className="space-y-3 p-4">
              <div>
                <p className="font-medium text-muted-foreground text-xs uppercase tracking-wider">
                  Agents {agents ? `(${agents.agents.length})` : ""}
                </p>
              </div>

              {agentsError && (
                <div className="rounded-lg bg-destructive/10 p-2">
                  <p className="text-destructive text-xs">{agentsError}</p>
                </div>
              )}

              {agents?.agents.map((m) => (
                <AgentCard
                  key={m.name}
                  manifest={m}
                  onShowGraph={() => setGraphScope(m.name)}
                />
              ))}

              {agents && agents.errors.length > 0 && (
                <>
                  <Separator className="my-2" />
                  <p className="font-medium text-muted-foreground text-xs uppercase tracking-wider">
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

        {/* Main content */}
        <main className="flex min-w-0 flex-1 flex-col">
          {/* Messages */}
          <Conversation className="min-h-0 flex-1">
            <ConversationContent className="mx-auto w-full max-w-2xl px-4 py-6">
              {timeline.length === 0 && (
                <ConversationEmptyState
                  title="Ask the supervisor"
                  description='Example: "What is (17 + 25) × 3?" or "Summarize this text"'
                />
              )}

              {timeline.map((item, i) => {
                if (item.kind === "route") return <RouteStep key={i} decision={item} />;
                if (item.kind === "tool") return <ToolCall key={i} item={item} />;
                if (item.kind === "notice")
                  return <NoticeCard key={i} detail={item.detail} onRetry={retry} />;
                return <ChatMessage key={i} item={item} />;
              })}

              {thinking && <ThinkingShimmer />}

              <ArtifactsCard artifacts={artifacts} />

              {error && (
                <div className="rounded-lg bg-destructive/10 p-3">
                  <p className="text-destructive text-xs">{error}</p>
                </div>
              )}
            </ConversationContent>
            <ConversationScrollButton />
          </Conversation>

          {/* Input area */}
          <div className="shrink-0 border-t border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="mx-auto w-full max-w-2xl space-y-3 px-4 py-4">
              <ActiveAgentIndicator agent={status === "streaming" ? activeAgent : null} />

              <form
                onSubmit={handleSubmit}
                className="space-y-2"
              >
                <PromptInputTextarea
                  placeholder="Ask anything — the supervisor will route it to the right agent…"
                  disabled={status === "streaming"}
                />
                <div className="flex justify-end">
                  <PromptInputSubmit
                    onStop={stop}
                    status={status === "streaming" ? "streaming" : "ready"}
                  />
                </div>
              </form>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
