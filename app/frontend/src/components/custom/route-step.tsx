"use client";

import { FlagIcon, SplitIcon } from "lucide-react";

import {
  ChainOfThought,
  ChainOfThoughtContent,
  ChainOfThoughtHeader,
  ChainOfThoughtStep,
} from "@/components/ai-elements/chain-of-thought";
import type { RouteItem } from "@/hooks/use-supervisor-chat";

/** Custom wrapper: one supervisor routing decision, rendered with the
 *  AI Elements ChainOfThought primitives. */
export function RouteStep({ decision }: { decision: RouteItem }) {
  const finished = decision.next === "FINISH";
  return (
    <ChainOfThought defaultOpen className="mb-2">
      <ChainOfThoughtHeader>
        supervisor → {decision.next}
      </ChainOfThoughtHeader>
      <ChainOfThoughtContent>
        <ChainOfThoughtStep
          icon={finished ? FlagIcon : SplitIcon}
          label={finished ? "FINISH" : `route to ${decision.next}`}
          description={decision.reason}
          status="complete"
        />
      </ChainOfThoughtContent>
    </ChainOfThought>
  );
}
