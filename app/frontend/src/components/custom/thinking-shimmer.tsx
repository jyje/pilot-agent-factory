"use client";

import { BrainIcon } from "lucide-react";

import { Shimmer } from "@/components/ai-elements/shimmer";

/** Custom wrapper: shimmering in-conversation placeholder for the silent
 * stretches of a turn — before the first token, or between agent handovers —
 * the "answer being drawn" loading pattern. Matches the Reasoning fold's
 * own shimmering "Thinking..." trigger. */
export function ThinkingShimmer({ label = "Thinking…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-muted-foreground text-sm">
      <BrainIcon className="size-4" />
      <Shimmer as="span" duration={1.5}>
        {label}
      </Shimmer>
    </div>
  );
}
