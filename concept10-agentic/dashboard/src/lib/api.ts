import type { ActiveRequest, AgentConfig } from "@/types/agents";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function fetchAgentGraph(): Promise<Record<string, string[]>> {
  const response = await fetch(`${API_BASE_URL}/agents/graph`);
  if (!response.ok) {
    throw new Error("Failed to load agent graph");
  }
  return response.json() as Promise<Record<string, string[]>>;
}

export async function fetchAgentConfigs(): Promise<AgentConfig[]> {
  const response = await fetch(`${API_BASE_URL}/agents?page=1&size=200`);
  if (!response.ok) {
    throw new Error("Failed to load agent configs");
  }
  const payload = (await response.json()) as { items: AgentConfig[] };
  return payload.items;
}

export async function fetchAgentConfig(agentId: string): Promise<AgentConfig> {
  const response = await fetch(`${API_BASE_URL}/agents/${agentId}`);
  if (!response.ok) {
    throw new Error("Failed to load agent config");
  }
  return response.json() as Promise<AgentConfig>;
}

export async function fetchActiveRequests(): Promise<ActiveRequest[]> {
  const response = await fetch(`${API_BASE_URL}/orchestrate/active`);
  if (response.status === 404) {
    return [];
  }
  if (!response.ok) {
    throw new Error("Failed to load active requests");
  }
  const payload = (await response.json()) as { items?: ActiveRequest[] } | ActiveRequest[];
  if (Array.isArray(payload)) {
    return payload;
  }
  return payload.items ?? [];
}
