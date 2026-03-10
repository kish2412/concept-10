export type AgentCategory = "orchestrator" | "utility" | "specialist" | "human-in-loop";

export interface AgentConfig {
  id: string;
  category: AgentCategory;
  version: string;
  description: string;
  prompt_template: string;
  input_schema: string;
  output_schema: string;
  tools: string[];
  governance_profile: string;
  langsmith_project: string;
  otel_service_name: string;
  human_review_required: boolean;
  max_context_tokens: number;
  tags?: string[];
}

export interface ActiveRequest {
  request_id: string;
  agent_id: string;
  elapsed_time: string;
  governance_flags: string[];
  current_node: string;
  trace_url?: string;
  otel_trace_id?: string;
  apm_link?: string;
  trace_steps?: Array<Record<string, unknown>>;
}
