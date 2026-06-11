"use client";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { AgentManifest, LoadError } from "@/lib/api";

/** Custom wrapper: renders one AgentManifest with shadcn Card/Badge.
 *  Clicking the card opens its graph structure (when onShowGraph is given). */
export function AgentCard({
  manifest,
  onShowGraph,
}: {
  manifest: AgentManifest;
  onShowGraph?: () => void;
}) {
  return (
    <Card
      className={`gap-2 py-4 ${onShowGraph ? "cursor-pointer transition-colors hover:bg-accent/50" : ""}`}
      onClick={onShowGraph}
      title={onShowGraph ? "Show graph structure" : undefined}
    >
      <CardHeader className="px-4">
        <CardTitle className="flex items-center gap-2 text-sm">
          <span className="size-2 rounded-full bg-green-500" />
          {manifest.name}
          <span className="font-normal text-muted-foreground text-xs">
            v{manifest.version}
          </span>
        </CardTitle>
        <CardDescription className="text-xs">{manifest.description}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-1 px-4">
        {manifest.capabilities.map((cap) => (
          <Badge key={cap} variant="secondary" className="text-xs">
            {cap}
          </Badge>
        ))}
        <Badge variant="outline" className="text-xs">
          sdk {manifest.sdk_version}
        </Badge>
      </CardContent>
    </Card>
  );
}

/** Custom wrapper: isolated load failures (Phase 3 invariant made visible). */
export function LoadErrorCard({ error }: { error: LoadError }) {
  return (
    <Card className="gap-1 border-destructive/50 py-3">
      <CardHeader className="px-4">
        <CardTitle className="text-destructive text-xs">{error.source}</CardTitle>
        <CardDescription className="break-all text-xs">{error.error}</CardDescription>
      </CardHeader>
    </Card>
  );
}
