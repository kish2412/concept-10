"use client";

import * as React from "react";
import {
  Controller,
  type ControllerProps,
  type FieldPath,
  type FieldValues,
  FormProvider,
  useFormContext,
} from "react-hook-form";

import { cn } from "@/lib/utils";

const Form = FormProvider;

const FormField = <
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>
>(
  props: ControllerProps<TFieldValues, TName>
) => {
  return <Controller {...props} />;
};

const FormItem = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className, ...props }, ref) => {
  return <div ref={ref} className={cn("space-y-2", className)} {...props} />;
});
FormItem.displayName = "FormItem";

const FormLabel = React.forwardRef<HTMLLabelElement, React.LabelHTMLAttributes<HTMLLabelElement>>(
  ({ className, ...props }, ref) => {
    return <label ref={ref} className={cn("text-sm font-medium", className)} {...props} />;
  }
);
FormLabel.displayName = "FormLabel";

const FormControl = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className, ...props }, ref) => {
  return <div ref={ref} className={cn(className)} {...props} />;
});
FormControl.displayName = "FormControl";

const FormMessage = ({ name }: { name: string }) => {
  const {
    formState: { errors },
  } = useFormContext();

  const message = errors[name as keyof typeof errors]?.message;
  if (!message || typeof message !== "string") {
    return null;
  }

  return <p className="text-sm text-red-600">{message}</p>;
};

export { Form, FormControl, FormField, FormItem, FormLabel, FormMessage };
