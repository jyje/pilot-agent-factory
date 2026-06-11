"use client";

import { RefreshCcwIcon, TriangleAlertIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

/** Custom wrapper: a non-fatal turn problem (e.g. the model produced no
 *  answer) with a one-click retry. */
export function NoticeCard({ detail, onRetry }: { detail: string; onRetry?: () => void }) {
  return (
    <Card className="mb-2 border-amber-500/50 py-3">
      <CardContent className="flex items-center gap-3 px-4">
        <TriangleAlertIcon className="size-4 shrink-0 text-amber-500" />
        <p className="flex-1 text-muted-foreground text-xs">{detail}</p>
        {onRetry && (
          <Button size="sm" variant="outline" onClick={onRetry}>
            <RefreshCcwIcon className="size-3" /> Retry
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
