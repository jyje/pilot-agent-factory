"use client";

import { PackageIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/** Custom wrapper: extra state channels lifted from agents' output_schema
 *  (e.g. summarizer.summary) — the supervisor's `artifacts` channel. */
export function ArtifactsCard({
  artifacts,
}: {
  artifacts: Record<string, Record<string, unknown>>;
}) {
  const entries = Object.entries(artifacts);
  if (entries.length === 0) return null;

  return (
    <Card className="mb-4 gap-2 py-4">
      <CardHeader className="px-4">
        <CardTitle className="flex items-center gap-2 text-sm">
          <PackageIcon className="size-4" /> artifacts
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 px-4">
        {entries.flatMap(([agent, extras]) =>
          Object.entries(extras).map(([key, value]) => (
            <div key={`${agent}.${key}`} className="space-y-1">
              <Badge variant="outline" className="text-xs">
                {agent}.{key}
              </Badge>
              <p className="whitespace-pre-wrap text-muted-foreground text-xs">
                {String(value)}
              </p>
            </div>
          )),
        )}
      </CardContent>
    </Card>
  );
}
