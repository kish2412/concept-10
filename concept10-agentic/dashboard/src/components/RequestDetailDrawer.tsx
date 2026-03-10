import { Copy, ExternalLink } from "lucide-react";
import { useMemo } from "react";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { Drawer, DrawerContent } from "@/components/ui/drawer";
import { useAgentStore } from "@/store/useAgentStore";

export default function RequestDetailDrawer() {
  const selectedRequestId = useAgentStore((s) => s.selectedRequestId);
  const setSelectedRequestId = useAgentStore((s) => s.setSelectedRequestId);
  const activeRequests = useAgentStore((s) => s.activeRequests);

  const item = useMemo(() => activeRequests.find((x) => x.request_id === selectedRequestId), [activeRequests, selectedRequestId]);

  const open = Boolean(selectedRequestId && item);

  return (
    <Drawer open={open} onOpenChange={(value) => !value && setSelectedRequestId(null)}>
      <DrawerContent>
        {!item ? null : (
          <div>
            <h2 className="text-lg font-semibold text-ink">Request Details</h2>
            <div className="mt-3 rounded-lg border border-slate-200 p-3">
              <div className="text-xs text-muted">request_id</div>
              <div className="mt-1 flex items-center justify-between gap-2 text-xs font-medium text-ink">
                <span className="truncate">{item.request_id}</span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => navigator.clipboard.writeText(item.request_id)}
                >
                  <Copy size={14} />
                </Button>
              </div>
            </div>

            <div className="mt-3 space-y-2 text-xs">
              <a className="flex items-center gap-1 text-orch hover:underline" href={item.trace_url} target="_blank" rel="noreferrer">
                LangSmith Trace <ExternalLink size={12} />
              </a>
              <a className="flex items-center gap-1 text-orch hover:underline" href={item.apm_link} target="_blank" rel="noreferrer">
                APM Trace ({item.otel_trace_id ?? "n/a"}) <ExternalLink size={12} />
              </a>
            </div>

            <div className="mt-4">
              <div className="mb-2 text-sm font-semibold text-ink">Trace Steps</div>
              <Accordion type="multiple" className="rounded border border-slate-200 px-3">
                {(item.trace_steps ?? []).map((step, idx) => (
                  <AccordionItem value={`step-${idx}`} key={`step-${idx}`}>
                    <AccordionTrigger>Step {idx + 1}</AccordionTrigger>
                    <AccordionContent>
                      <pre className="overflow-auto whitespace-pre-wrap text-[11px] text-muted">{JSON.stringify(step, null, 2)}</pre>
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            </div>

            <div className="mt-4">
              <div className="mb-2 text-sm font-semibold text-ink">Governance Flags</div>
              <ul className="space-y-1 text-xs text-muted">
                {(item.governance_flags ?? []).map((flag) => (
                  <li key={flag} className="rounded bg-slate-100 px-2 py-1">
                    {flag}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </DrawerContent>
    </Drawer>
  );
}
