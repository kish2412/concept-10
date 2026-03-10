import { useQuery } from "@tanstack/react-query";
import { fetchAgentConfig } from "@/lib/api";
import { useAgentStore } from "@/store/useAgentStore";

export default function AgentConfigPanel() {
  const selectedAgentId = useAgentStore((s) => s.selectedAgentId);

  const query = useQuery({
    queryKey: ["agent-config", selectedAgentId],
    queryFn: () => fetchAgentConfig(selectedAgentId as string),
    enabled: Boolean(selectedAgentId),
  });

  return (
    <section className="w-[320px] rounded-2xl border border-slate-200 bg-panel p-4 shadow-card">
      <h3 className="text-sm font-semibold text-ink">Agent Config</h3>
      {!selectedAgentId && <p className="mt-2 text-xs text-muted">Click an agent node to view details.</p>}
      {selectedAgentId && query.isLoading && <p className="mt-2 text-xs text-muted">Loading...</p>}
      {query.data && (
        <div className="mt-3 space-y-2 text-xs">
          {Object.entries(query.data)
            .filter(([key]) => !key.toLowerCase().includes("key") && !key.toLowerCase().includes("secret"))
            .map(([key, value]) => (
              <div key={key} className="rounded border border-slate-200 p-2">
                <div className="font-semibold text-ink">{key}</div>
                <div className="mt-1 break-words text-muted">{typeof value === "string" ? value : JSON.stringify(value)}</div>
              </div>
            ))}
        </div>
      )}
    </section>
  );
}
