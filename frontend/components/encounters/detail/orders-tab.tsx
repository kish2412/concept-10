"use client";

import { useCallback, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAddOrder, useUpdateOrderStatus } from "@/lib/use-encounter-detail";
import {
  ORDER_PRIORITIES,
  ORDER_STATUSES,
  ORDER_TYPE_LABELS,
  ORDER_TYPES,
} from "@/types/encounter-detail";
import type { Encounter, OrderRecord } from "@/types/encounter-queue";
import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  ClipboardList,
  FileText,
  FlaskConical,
  Image,
  Link,
  Pill,
  Plus,
  Send,
  Stethoscope,
  Zap,
} from "lucide-react";

type Props = {
  encounter: Encounter;
  readOnly: boolean;
};

const ORDER_TYPE_ICON: Record<string, React.ElementType> = {
  LAB: FlaskConical,
  IMAGING: Image,
  MEDICATION: Pill,
  REFERRAL: Send,
};

const STATUS_STEP: Record<string, number> = {
  PENDING: 0,
  SENT: 1,
  IN_PROGRESS: 2,
  RESULTED: 3,
};

function StatusTracker({ status }: { status: string }) {
  const step = STATUS_STEP[status] ?? 0;
  return (
    <div className="flex items-center gap-1">
      {ORDER_STATUSES.map((s, i) => (
        <div key={s} className="flex items-center gap-1">
          <div
            className={`h-2 w-2 rounded-full ${
              i <= step ? "bg-primary" : "bg-muted"
            }`}
          />
          {i < ORDER_STATUSES.length - 1 && (
            <div
              className={`h-0.5 w-4 ${
                i < step ? "bg-primary" : "bg-muted"
              }`}
            />
          )}
        </div>
      ))}
      <span className="text-[10px] text-muted-foreground ml-1">
        {status.replace("_", " ")}
      </span>
    </div>
  );
}

function OrderResultView({ order }: { order: OrderRecord }) {
  if (!order.result_summary) return null;
  const isPdf = /\.pdf($|\?)/i.test(order.result_summary) ||
    /^https?:\/\/.+\.pdf($|\?)/i.test(order.result_summary);

  if (isPdf) {
    return (
      <div className="mt-2 rounded border bg-muted/30 p-3 text-sm space-y-2">
        <span className="font-medium text-muted-foreground text-xs">Result (PDF):</span>
        <a
          href={order.result_summary}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-primary underline"
        >
          <FileText className="h-3.5 w-3.5" />
          Open result PDF
        </a>
      </div>
    );
  }

  return (
    <div className="mt-2 rounded border bg-muted/30 p-3 text-sm">
      <span className="font-medium text-muted-foreground text-xs">Result:</span>
      <p className="mt-1 whitespace-pre-wrap">{order.result_summary}</p>
    </div>
  );
}

export function OrdersTab({ encounter, readOnly }: Props) {
  const [showForm, setShowForm] = useState(false);
  const [orderType, setOrderType] = useState<string>("LAB");
  const [orderDesc, setOrderDesc] = useState("");
  const [orderCode, setOrderCode] = useState("");
  const [priority, setPriority] = useState<string>("ROUTINE");
  const [clinicalInfo, setClinicalInfo] = useState("");
  const [reasonForOrder, setReasonForOrder] = useState("");
  const [specimen, setSpecimen] = useState("");
  const [targetDepartment, setTargetDepartment] = useState("");
  const [referralTo, setReferralTo] = useState("");
  const [expandedOrders, setExpandedOrders] = useState<Set<string>>(new Set());

  const addOrder = useAddOrder(encounter.id);
  const updateOrderStatus = useUpdateOrderStatus(encounter.id);

  const handleSubmit = useCallback(() => {
    if (!orderDesc.trim()) return;
    const composedDescription = [
      orderDesc.trim(),
      reasonForOrder.trim() ? `Reason: ${reasonForOrder.trim()}` : "",
      clinicalInfo.trim() ? `Clinical info: ${clinicalInfo.trim()}` : "",
      specimen.trim() ? `Specimen: ${specimen.trim()}` : "",
      targetDepartment.trim() ? `Department: ${targetDepartment.trim()}` : "",
      referralTo.trim() ? `Referral to: ${referralTo.trim()}` : "",
    ]
      .filter(Boolean)
      .join("\n");

    addOrder.mutate(
      {
        order_type: orderType,
        order_description: composedDescription,
        order_code: orderCode || undefined,
        priority,
      },
      {
        onSuccess: () => {
          setOrderDesc("");
          setOrderCode("");
          setPriority("ROUTINE");
          setClinicalInfo("");
          setReasonForOrder("");
          setSpecimen("");
          setTargetDepartment("");
          setReferralTo("");
          setShowForm(false);
        },
      }
    );
  }, [
    addOrder,
    orderDesc,
    reasonForOrder,
    clinicalInfo,
    specimen,
    targetDepartment,
    referralTo,
    orderType,
    orderCode,
    priority,
  ]);

  const handleStatusChange = (orderId: string, status: string) => {
    updateOrderStatus.mutate({ orderId, status });
  };

  const toggleExpanded = (id: string) => {
    setExpandedOrders((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Group orders by type
  const grouped: Record<string, OrderRecord[]> = {};
  for (const order of encounter.orders) {
    const type = order.order_type;
    if (!grouped[type]) grouped[type] = [];
    grouped[type].push(order);
  }

  return (
    <div className="space-y-6">
      {/* Add order button */}
      {!readOnly && (
        <div>
          {!showForm ? (
            <Button size="sm" onClick={() => setShowForm(true)}>
              <Plus className="h-3.5 w-3.5 mr-1" />
              New Order
            </Button>
          ) : (
            <div className="rounded-lg border p-4 space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold">New Order</h4>
                <Button variant="ghost" size="sm" onClick={() => setShowForm(false)}>
                  Cancel
                </Button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs">Type</Label>
                  <Select value={orderType} onValueChange={setOrderType}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ORDER_TYPES.map((t) => (
                        <SelectItem key={t} value={t}>
                          {ORDER_TYPE_LABELS[t]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">Priority</Label>
                  <Select value={priority} onValueChange={setPriority}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ORDER_PRIORITIES.map((p) => (
                        <SelectItem key={p} value={p}>
                          {p}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">Order Code (optional)</Label>
                  <Input
                    value={orderCode}
                    onChange={(e) => setOrderCode(e.target.value)}
                    placeholder="e.g., CPT, LOINC"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs">Description</Label>
                <Textarea
                  value={orderDesc}
                  onChange={(e) => setOrderDesc(e.target.value)}
                  placeholder={
                    orderType === "LAB"
                      ? "e.g., CBC with differential, BMP, HbA1c..."
                      : orderType === "IMAGING"
                        ? "e.g., Chest X-Ray PA and Lateral..."
                        : orderType === "MEDICATION"
                          ? "e.g., Amoxicillin 500mg PO TID x7 days..."
                          : "e.g., Refer to Cardiology for evaluation..."
                  }
                  className="min-h-[80px]"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-xs">Reason for Order</Label>
                  <Input
                    value={reasonForOrder}
                    onChange={(e) => setReasonForOrder(e.target.value)}
                    placeholder="Clinical reason"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">Clinical Info</Label>
                  <Input
                    value={clinicalInfo}
                    onChange={(e) => setClinicalInfo(e.target.value)}
                    placeholder="Pertinent findings"
                  />
                </div>

                {orderType === "LAB" && (
                  <div className="space-y-1.5">
                    <Label className="text-xs">Specimen</Label>
                    <Input
                      value={specimen}
                      onChange={(e) => setSpecimen(e.target.value)}
                      placeholder="e.g., Blood, Urine"
                    />
                  </div>
                )}

                {orderType === "IMAGING" && (
                  <div className="space-y-1.5">
                    <Label className="text-xs">Department</Label>
                    <Input
                      value={targetDepartment}
                      onChange={(e) => setTargetDepartment(e.target.value)}
                      placeholder="e.g., Radiology"
                    />
                  </div>
                )}

                {orderType === "REFERRAL" && (
                  <div className="space-y-1.5">
                    <Label className="text-xs">Referral To</Label>
                    <Input
                      value={referralTo}
                      onChange={(e) => setReferralTo(e.target.value)}
                      placeholder="e.g., Cardiology"
                    />
                  </div>
                )}
              </div>

              <div className="flex justify-end">
                <Button onClick={handleSubmit} disabled={!orderDesc.trim() || addOrder.isPending}>
                  {addOrder.isPending ? "Placing..." : "Place Order"}
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Orders list grouped by type */}
      {encounter.orders.length === 0 ? (
        <div className="text-center py-8 text-sm text-muted-foreground">
          <ClipboardList className="h-8 w-8 mx-auto mb-2 opacity-50" />
          No orders placed yet
        </div>
      ) : (
        <div className="space-y-5">
          {Object.entries(grouped).map(([type, orders]) => {
            const Icon = ORDER_TYPE_ICON[type] ?? Stethoscope;
            return (
              <div key={type} className="space-y-2">
                <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground flex items-center gap-1.5">
                  <Icon className="h-3.5 w-3.5" />
                  {ORDER_TYPE_LABELS[type as keyof typeof ORDER_TYPE_LABELS] ?? type} ({orders.length})
                </h4>
                <div className="space-y-2">
                  {orders.map((order) => {
                    const expanded = expandedOrders.has(order.id);
                    const isResulted = order.status === "RESULTED";
                    return (
                      <div
                        key={order.id}
                        className="rounded-md border px-3 py-2.5 space-y-2"
                      >
                        <div className="flex items-start gap-2">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium truncate">
                                {order.order_description}
                              </span>
                              {order.priority === "STAT" && (
                                <Badge className="bg-red-600 text-white text-[10px] shrink-0">
                                  <Zap className="h-3 w-3 mr-0.5" />
                                  STAT
                                </Badge>
                              )}
                              {order.priority === "URGENT" && (
                                <Badge className="bg-orange-500 text-white text-[10px] shrink-0">
                                  <AlertTriangle className="h-3 w-3 mr-0.5" />
                                  URGENT
                                </Badge>
                              )}
                            </div>
                            {order.order_code && (
                              <span className="text-xs text-muted-foreground font-mono">
                                {order.order_code}
                              </span>
                            )}
                          </div>
                          <div className="space-y-1">
                            <StatusTracker status={order.status} />
                            {!readOnly && (
                              <Select
                                value={order.status}
                                onValueChange={(nextStatus) => handleStatusChange(order.id, nextStatus)}
                              >
                                <SelectTrigger className="h-7 w-[150px] text-xs">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  {ORDER_STATUSES.map((s) => (
                                    <SelectItem key={s} value={s}>
                                      {s.replace("_", " ")}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            )}
                          </div>
                          {isResulted && order.result_summary && (
                            <button
                              onClick={() => toggleExpanded(order.id)}
                              className="text-muted-foreground hover:text-foreground"
                            >
                              {expanded ? (
                                <ChevronUp className="h-4 w-4" />
                              ) : (
                                <ChevronDown className="h-4 w-4" />
                              )}
                            </button>
                          )}
                        </div>
                        {expanded && <OrderResultView order={order} />}
                        {isResulted && order.result_summary && !expanded && (
                          <button
                            onClick={() => toggleExpanded(order.id)}
                            className="inline-flex items-center gap-1 text-xs text-primary"
                          >
                            <Link className="h-3.5 w-3.5" />
                            View result
                          </button>
                        )}
                        <div className="text-xs text-muted-foreground">
                          Ordered {order.ordered_at ? new Date(order.ordered_at).toLocaleString() : new Date(order.created_at).toLocaleString()}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
