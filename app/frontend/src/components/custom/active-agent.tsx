"use client";

import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";

/** Custom wrapper: which agent is generating right now (token attribution). */
export function ActiveAgentIndicator({ agent }: { agent: string | null }) {
  if (!agent) return null;
  return (
    <div className="flex items-center gap-2 px-1 pb-2 text-muted-foreground text-xs">
      <Spinner className="size-3" />
      <Badge variant={agent === "supervisor" ? "secondary" : "default"} className="text-xs">
        {agent}
      </Badge>
      is working…
    </div>
  );
}
