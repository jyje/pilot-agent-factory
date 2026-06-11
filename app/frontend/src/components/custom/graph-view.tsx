"use client";

import { useEffect, useId, useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { fetchGraph } from "@/lib/api";

/** Custom wrapper: renders Mermaid source to SVG (client-side only). */
export function MermaidDiagram({ code }: { code: string }) {
  const reactId = useId().replace(/[^a-zA-Z0-9]/g, "");
  const [svg, setSvg] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({ startOnLoad: false, securityLevel: "loose", theme: "neutral" });
        const { svg } = await mermaid.render(`mmd${reactId}`, code);
        if (!cancelled) setSvg(svg);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [code, reactId]);

  if (error) return <p className="text-destructive text-xs">{error}</p>;
  if (!svg) return <p className="text-muted-foreground text-xs">rendering…</p>;
  return (
    <div
      className="overflow-auto [&_svg]:mx-auto [&_svg]:h-auto [&_svg]:max-w-full"
      // mermaid output is generated locally from our own API's graph source
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}

/** Graph structure dialog: platform overview, top-level graph, or one agent. */
export function GraphDialog({
  scope,
  onClose,
}: {
  scope: string | null; // null → closed, "" → platform overview
  onClose: () => void;
}) {
  const [code, setCode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (scope === null) return;
    setCode(null);
    setError(null);
    fetchGraph(scope || undefined)
      .then((r) => setCode(r.mermaid))
      .catch((e) => setError(String(e)));
  }, [scope]);

  const title =
    scope === "" ? "Platform structure" : scope === "top" ? "Deep supervisor graph" : `${scope} graph`;

  return (
    <Dialog open={scope !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            Live structure from the registry — compiled LangGraph topology rendered as Mermaid.
          </DialogDescription>
        </DialogHeader>
        {error && <p className="text-destructive text-xs">{error}</p>}
        {code && <MermaidDiagram code={code} />}
      </DialogContent>
    </Dialog>
  );
}
