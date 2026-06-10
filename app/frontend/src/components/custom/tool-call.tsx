"use client";

import {
  Tool,
  ToolContent,
  ToolHeader,
  ToolInput,
  ToolOutput,
} from "@/components/ai-elements/tool";
import type { ToolItem } from "@/hooks/use-supervisor-chat";

/** Custom wrapper: maps our backend's {name, args, output} tool events onto
 *  the AI Elements Tool part shape (`tool-<name>` / state). */
export function ToolCall({ item }: { item: ToolItem }) {
  const state = item.output === undefined ? "input-available" : "output-available";
  return (
    <Tool defaultOpen={false}>
      <ToolHeader type={`tool-${item.name}`} state={state} />
      <ToolContent>
        <ToolInput input={item.args} />
        {item.output !== undefined && (
          <ToolOutput errorText={undefined} output={item.output} />
        )}
      </ToolContent>
    </Tool>
  );
}
