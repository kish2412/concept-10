import { create } from "zustand";
import type { Edge, Node } from "reactflow";
import type { ActiveRequest, AgentConfig } from "@/types/agents";

interface AgentStore {
  nodes: Node[];
  edges: Edge[];
  activeRequests: ActiveRequest[];
  selectedAgentId: string | null;
  selectedRequestId: string | null;
  agentConfigs: Record<string, AgentConfig>;
  setGraph: (nodes: Node[], edges: Edge[]) => void;
  setActiveRequests: (items: ActiveRequest[]) => void;
  setSelectedAgentId: (agentId: string | null) => void;
  setSelectedRequestId: (requestId: string | null) => void;
  upsertAgentConfigs: (configs: AgentConfig[]) => void;
}

export const useAgentStore = create<AgentStore>((set) => ({
  nodes: [],
  edges: [],
  activeRequests: [],
  selectedAgentId: null,
  selectedRequestId: null,
  agentConfigs: {},
  setGraph: (nodes, edges) => set({ nodes, edges }),
  setActiveRequests: (activeRequests) => set({ activeRequests }),
  setSelectedAgentId: (selectedAgentId) => set({ selectedAgentId }),
  setSelectedRequestId: (selectedRequestId) => set({ selectedRequestId }),
  upsertAgentConfigs: (configs) =>
    set((state) => ({
      agentConfigs: {
        ...state.agentConfigs,
        ...Object.fromEntries(configs.map((config) => [config.id, config])),
      },
    })),
}));
