"use client";

import { useEffect, useRef, useState } from "react";
import { Bold, Italic, List, ListOrdered, Underline } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type RichTextEditorProps = {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
};

export function RichTextEditor({
  value,
  onChange,
  placeholder,
  disabled,
  className,
}: RichTextEditorProps) {
  const editorRef = useRef<HTMLDivElement | null>(null);
  const [focused, setFocused] = useState(false);

  useEffect(() => {
    if (!editorRef.current) return;
    if (editorRef.current.innerHTML !== value) {
      editorRef.current.innerHTML = value || "";
    }
  }, [value]);

  const exec = (command: string) => {
    if (disabled) return;
    editorRef.current?.focus();
    document.execCommand(command, false);
    onChange(editorRef.current?.innerHTML ?? "");
  };

  const onInput = () => {
    onChange(editorRef.current?.innerHTML ?? "");
  };

  const showPlaceholder = !value?.trim() && !focused;

  return (
    <div
      className={cn(
        "rounded-md border bg-background",
        disabled && "opacity-60",
        className
      )}
    >
      <div className="flex items-center gap-1 border-b px-2 py-1.5">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => exec("bold")}
          disabled={disabled}
          className="h-7 px-2"
          title="Bold"
        >
          <Bold className="h-3.5 w-3.5" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => exec("italic")}
          disabled={disabled}
          className="h-7 px-2"
          title="Italic"
        >
          <Italic className="h-3.5 w-3.5" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => exec("underline")}
          disabled={disabled}
          className="h-7 px-2"
          title="Underline"
        >
          <Underline className="h-3.5 w-3.5" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => exec("insertUnorderedList")}
          disabled={disabled}
          className="h-7 px-2"
          title="Bulleted list"
        >
          <List className="h-3.5 w-3.5" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => exec("insertOrderedList")}
          disabled={disabled}
          className="h-7 px-2"
          title="Numbered list"
        >
          <ListOrdered className="h-3.5 w-3.5" />
        </Button>
      </div>

      <div className="relative">
        {showPlaceholder && placeholder ? (
          <span className="pointer-events-none absolute left-3 top-3 text-sm text-muted-foreground">
            {placeholder}
          </span>
        ) : null}
        <div
          ref={editorRef}
          contentEditable={!disabled}
          suppressContentEditableWarning
          onInput={onInput}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          className="min-h-[120px] px-3 py-2 text-sm outline-none"
        />
      </div>
    </div>
  );
}
