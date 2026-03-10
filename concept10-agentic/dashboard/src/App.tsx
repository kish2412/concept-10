import AgentConfigPanel from "@/components/AgentConfigPanel";
import AgentGraphView from "@/components/AgentGraphView";
import ActiveRequestOverlay from "@/components/ActiveRequestOverlay";
import RequestDetailDrawer from "@/components/RequestDetailDrawer";

export default function App() {
  return (
    <div className="h-full p-4 md:p-6">
      <header className="mb-4 md:mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-ink">Agent Orchestration Dashboard</h1>
        <p className="mt-1 text-sm text-muted">Live topology, active requests, and agent configuration</p>
      </header>

      <main className="grid h-[calc(100%-5.5rem)] grid-cols-1 gap-4 xl:grid-cols-[1fr_340px]">
        <section className="grid min-h-0 grid-cols-1 gap-4 lg:grid-cols-[1fr_320px]">
          <div className="min-h-0">
            <AgentGraphView />
          </div>
          <AgentConfigPanel />
        </section>

        <ActiveRequestOverlay />
      </main>

      <RequestDetailDrawer />
    </div>
  );
}
