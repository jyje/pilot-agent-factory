"use client";

import { Shimmer } from "@/components/ai-elements/shimmer";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";

/** Custom wrapper: which agent is generating right now (token attribution).
 * The supervisor is the default speaker, so it works unnamed. */
export function ActiveAgentIndicator({ agent }: { agent: string | null }) {
  if (!agent) return null;
  return (
    <div className="flex items-center gap-2 px-1 pb-2 text-muted-foreground text-xs">
      <Spinner className="size-3" />
      {agent === "supervisor" ? (
        <Shimmer as="span" duration={1.5} className="text-xs">
          Thinking…
        </Shimmer>
      ) : (
        <>
          <Badge variant="default" className="text-xs">
            {agent}
          </Badge>
          <Shimmer as="span" duration={1.5} className="text-xs">
            is working…
          </Shimmer>
        </>
      )}
    </div>
  );
}
