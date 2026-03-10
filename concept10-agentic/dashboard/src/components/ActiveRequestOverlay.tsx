import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity } from "lucide-react";
import { fetchActiveRequests } from "@/lib/api";
import { useAgentStore } from "@/store/useAgentStore";

export default function ActiveRequestOverlay() {
  const setActiveRequests = useAgentStore((s) => s.setActiveRequests);
  const activeRequests = useAgentStore((s) => s.activeRequests);
  const setSelectedRequestId = useAgentStore((s) => s.setSelectedRequestId);

  const query = useQuery({
    queryKey: ["active-requests"],
    queryFn: fetchActiveRequests,
    refetchInterval: 3000,
  });

  useEffect(() => {
    if (query.data) {
      setActiveRequests(query.data);
    }
  }, [query.data, setActiveRequests]);

  return (
    <aside className="w-[340px] rounded-2xl border border-slate-200 bg-panel p-4 shadow-card">
      <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-ink">
        <Activity size={16} /> Active Requests
      </div>
      <div className="space-y-2">
        {activeRequests.length === 0 && <div className="text-xs text-muted">No running requests</div>}
        {activeRequests.map((req) => (
          <button
            key={req.request_id}
            className="w-full rounded-xl border border-slate-200 bg-white p-3 text-left hover:border-slate-400"
            onClick={() => setSelectedRequestId(req.request_id)}
          >
            <div className="truncate text-xs font-semibold text-ink">{req.request_id}</div>
            <div className="mt-1 text-xs text-muted">agent: {req.agent_id}</div>
            <div className="mt-1 text-xs text-muted">elapsed: {req.elapsed_time ?? "--"}</div>
            <div className="mt-1 text-xs text-muted">flags: {req.governance_flags?.length ?? 0}</div>
            <div className="mt-1 text-xs text-muted">node: {req.current_node ?? "--"}</div>
          </button>
        ))}
      </div>
    </aside>
  );
}
