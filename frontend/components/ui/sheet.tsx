"use client";

import * as React from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";

import { cn } from "@/lib/utils";

const Sheet = Dialog.Root;
const SheetTrigger = Dialog.Trigger;
const SheetClose = Dialog.Close;

const SheetPortal = ({ ...props }: Dialog.DialogPortalProps) => <Dialog.Portal {...props} />;

const SheetOverlay = React.forwardRef<
  React.ElementRef<typeof Dialog.Overlay>,
  React.ComponentPropsWithoutRef<typeof Dialog.Overlay>
>(({ className, ...props }, ref) => (
  <Dialog.Overlay
    className={cn("fixed inset-0 z-50 bg-black/40 data-[state=open]:animate-in data-[state=closed]:animate-out", className)}
    {...props}
    ref={ref}
  />
));
SheetOverlay.displayName = Dialog.Overlay.displayName;

const SheetContent = React.forwardRef<
  React.ElementRef<typeof Dialog.Content>,
  React.ComponentPropsWithoutRef<typeof Dialog.Content>
>(({ className, children, ...props }, ref) => (
  <SheetPortal>
    <SheetOverlay />
    <Dialog.Content
      ref={ref}
      className={cn(
        "fixed right-0 top-0 z-50 h-full w-full max-w-md border-l bg-background p-6 shadow-lg",
        className
      )}
      {...props}
    >
      {children}
      <SheetClose className="absolute right-4 top-4 rounded-sm opacity-70 transition-opacity hover:opacity-100">
        <X className="h-4 w-4" />
      </SheetClose>
    </Dialog.Content>
  </SheetPortal>
));
SheetContent.displayName = Dialog.Content.displayName;

const SheetHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex flex-col space-y-1.5 text-left", className)} {...props} />
);

const SheetTitle = React.forwardRef<
  React.ElementRef<typeof Dialog.Title>,
  React.ComponentPropsWithoutRef<typeof Dialog.Title>
>(({ className, ...props }, ref) => <Dialog.Title ref={ref} className={cn("text-lg font-semibold", className)} {...props} />);
SheetTitle.displayName = Dialog.Title.displayName;

const SheetDescription = React.forwardRef<
  React.ElementRef<typeof Dialog.Description>,
  React.ComponentPropsWithoutRef<typeof Dialog.Description>
>(({ className, ...props }, ref) => (
  <Dialog.Description ref={ref} className={cn("text-sm text-muted-foreground", className)} {...props} />
));
SheetDescription.displayName = Dialog.Description.displayName;

export { Sheet, SheetTrigger, SheetClose, SheetContent, SheetHeader, SheetTitle, SheetDescription };
