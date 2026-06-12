"use client";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { CornerDownLeftIcon, SquareIcon } from "lucide-react";
import { useCallback, useRef } from "react";

export type PromptInputMessage = {
  text?: string;
};

export function PromptInputTextarea({
  placeholder,
  disabled,
}: {
  placeholder?: string;
  disabled?: boolean;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey && !disabled) {
        e.preventDefault();
        const form = e.currentTarget.closest("form");
        if (form) {
          form.requestSubmit();
        }
      }
    },
    [disabled]
  );

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    // Auto-resize
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 200) + "px";
  };

  return (
    <textarea
      ref={textareaRef}
      name="prompt"
      onChange={handleChange}
      onKeyDown={handleKeyDown}
      placeholder={placeholder}
      disabled={disabled}
      className={cn(
        "w-full rounded-lg border border-input bg-background px-3 py-2",
        "text-sm resize-none",
        "placeholder:text-muted-foreground",
        "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
        "disabled:cursor-not-allowed disabled:opacity-50"
      )}
      rows={3}
    />
  );
}

export function PromptInputSubmit({
  onStop,
  status,
}: {
  onStop?: () => void;
  status: "ready" | "streaming";
}) {
  const isStreaming = status === "streaming";

  return (
    <Button
      size="sm"
      variant={isStreaming ? "outline" : "default"}
      onClick={isStreaming ? onStop : undefined}
      className="gap-1"
      type={isStreaming ? "button" : "submit"}
      title={isStreaming ? "Stop generation (Esc)" : "Send message (Enter)"}
    >
      {isStreaming ? (
        <>
          <SquareIcon className="size-4" />
          Stop
        </>
      ) : (
        <>
          <CornerDownLeftIcon className="size-4" />
          Send
        </>
      )}
    </Button>
  );
}
