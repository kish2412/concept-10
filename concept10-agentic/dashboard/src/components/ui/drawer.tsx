import * as React from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export const Drawer = Dialog.Root;
export const DrawerTrigger = Dialog.Trigger;
export const DrawerClose = Dialog.Close;

export function DrawerContent({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <Dialog.Portal>
      <Dialog.Overlay className="fixed inset-0 bg-black/30" />
      <Dialog.Content className={cn("fixed right-0 top-0 h-full w-[420px] max-w-[95vw] bg-panel p-4 shadow-2xl", className)}>
        <Dialog.Close className="absolute right-4 top-4 rounded p-1 text-muted hover:bg-slate-100" aria-label="Close">
          <X size={16} />
        </Dialog.Close>
        {children}
      </Dialog.Content>
    </Dialog.Portal>
  );
}
