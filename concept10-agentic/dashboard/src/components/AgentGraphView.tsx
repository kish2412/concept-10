import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import ReactFlow, { Background, Controls, MarkerType, type Edge, type Node } from "reactflow";
import { fetchAgentConfigs, fetchAgentGraph } from "@/lib/api";
import { formatAgentName } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { useAgentStore } from "@/store/useAgentStore";
import type { AgentCategory } from "@/types/agents";

const categoryColor: Record<AgentCategory, string> = {
  orchestrator: "#1d4ed8",
  utility: "#047857",
  specialist: "#b45309",
  "human-in-loop": "#b91c1c",
};

function AgentNodeCard({ data }: { data: { id: string; category: AgentCategory; version: string; active?: boolean; requestId?: string } }) {
  return (
    <div
      className="min-w-[200px] rounded-xl border bg-panel p-3 shadow-card"
      style={{ borderColor: categoryColor[data.category] }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="text-sm font-semibold text-ink">{formatAgentName(data.id)}</div>
        <Badge className="text-white" style={{ backgroundColor: categoryColor[data.category] }}>
          {data.category}
        </Badge>
      </div>
      <div className="mt-2 text-xs text-muted">{data.version}</div>
      {data.active && <div className="mt-2 h-2 w-2 rounded-full bg-orch animate-pulseRing" />}
      {data.requestId && <div className="mt-2 rounded bg-slate-100 px-2 py-1 text-[10px] text-slate-700">{data.requestId}</div>}
    </div>
  );
}

const nodeTypes = { agentNode: AgentNodeCard };

export default function AgentGraphView() {
  const setGraph = useAgentStore((s) => s.setGraph);
  const setSelectedAgentId = useAgentStore((s) => s.setSelectedAgentId);
  const activeRequests = useAgentStore((s) => s.activeRequests);
  const nodes = useAgentStore((s) => s.nodes);
  const edges = useAgentStore((s) => s.edges);
  const upsertAgentConfigs = useAgentStore((s) => s.upsertAgentConfigs);

  const graphQuery = useQuery({ queryKey: ["agent-graph"], queryFn: fetchAgentGraph });
  const configQuery = useQuery({ queryKey: ["agent-configs"], queryFn: fetchAgentConfigs });

  useEffect(() => {
    if (configQuery.data) {
      upsertAgentConfigs(configQuery.data);
    }
  }, [configQuery.data, upsertAgentConfigs]);

  useEffect(() => {
    if (!graphQuery.data || !configQuery.data) {
      return;
    }

    const ids = Array.from(new Set([...Object.keys(graphQuery.data), ...Object.values(graphQuery.data).flat()]));
    const byId = Object.fromEntries(configQuery.data.map((cfg) => [cfg.id, cfg]));

    const builtNodes: Node[] = ids.map((id, index) => {
      const cfg = byId[id];
      const active = activeRequests.find((item) => item.agent_id === id);
      return {
        id,
        type: "agentNode",
        position: {
          x: 220 + (index % 4) * 260,
          y: 90 + Math.floor(index / 4) * 190,
        },
        sourcePosition: "right",
        targetPosition: "left",
        data: {
          id,
          category: cfg?.category ?? "utility",
          version: cfg?.version ?? "0.0.0",
          active: Boolean(active),
          requestId: active?.request_id,
        },
      };
    });

    const builtEdges: Edge[] = Object.entries(graphQuery.data).flatMap(([source, targets], sourceIndex) =>
      targets.map((target, targetIndex) => ({
        id: `${source}-${target}-${targetIndex}`,
        source,
        target,
        animated: true,
        markerEnd: { type: MarkerType.ArrowClosed, width: 20, height: 20 },
        style: { stroke: "#334155", strokeWidth: 1.7 },
        label: sourceIndex === 0 ? "delegates" : undefined,
      }))
    );

    setGraph(builtNodes, builtEdges);
  }, [activeRequests, configQuery.data, graphQuery.data, setGraph]);

  if (graphQuery.isLoading || configQuery.isLoading) {
    return <div className="flex h-full items-center justify-center text-muted">Loading graph...</div>;
  }

  return (
    <div className="h-full rounded-2xl border border-slate-200 bg-white">
      <ReactFlow
        fitView
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) => setSelectedAgentId(node.id)}
      >
        <Background gap={20} color="#e2e8f0" />
        <Controls />
      </ReactFlow>
    </div>
  );
}
