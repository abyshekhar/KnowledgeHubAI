import { FileCheck, Files, MessageSquare, Users } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { StatTile } from "../components/StatTile";

type LlmStatus = {
  provider: string;
  default_model: string;
  running: boolean;
  models: string[];
};

export function Dashboard({
  token,
  selectedModel,
  onSelectModel
}: {
  token: string;
  selectedModel: string;
  onSelectModel: (model: string) => void;
}) {
  const { data: metrics } = useQuery({
    queryKey: ["dashboard-metrics"],
    queryFn: () =>
      api<{
        total_documents: number;
        total_chunks: number;
        total_users: number;
        feedback_count: number;
      }>("/analytics/dashboard", token)
  });

  const llmStatusQuery = useQuery({
    queryKey: ["llm-status"],
    queryFn: () => api<LlmStatus>("/chat/models", token),
    refetchInterval: 15000
  });

  const llmStatus = llmStatusQuery.data;
  const activeModel = selectedModel || llmStatus?.default_model || "";

  return (
    <>
      <PageHeader title="Dashboard" subtitle="Operational overview for offline knowledge operations." />
      <div className="grid grid-cols-4 gap-4">
        <StatTile label="Total documents" value={metrics?.total_documents?.toString() ?? "0"} icon={Files} />
        <StatTile label="Total chunks" value={metrics?.total_chunks?.toString() ?? "0"} icon={FileCheck} />
        <StatTile label="Total users" value={metrics?.total_users?.toString() ?? "0"} icon={Users} />
        <StatTile label="Feedback count" value={metrics?.feedback_count?.toString() ?? "0"} icon={MessageSquare} />
      </div>
      <section className="mt-6 grid grid-cols-[1.2fr_0.8fr] gap-4">
        <div className="rounded-md border border-line bg-white">
          <div className="border-b border-line px-4 py-3 font-medium">AI Metrics</div>
          <div className="grid grid-cols-3 gap-4 p-4 text-sm">
            <Metric label="Avg retrieval" value="< 2s target" />
            <Metric label="Avg generation" value="< 10s target" />
            <Metric label="Failed searches" value="0" />
          </div>
        </div>
        <div className="rounded-md border border-line bg-white">
          <div className="border-b border-line px-4 py-3 font-medium">Local Model Runtime</div>
          <div className="space-y-3 p-4 text-sm">
            <div className="flex items-center gap-2">
              <span
                className={`h-2.5 w-2.5 rounded-full ${
                  llmStatusQuery.isLoading
                    ? "animate-pulse bg-slate-300"
                    : llmStatus?.running
                    ? "bg-emerald-500"
                    : "bg-red-500"
                }`}
              />
              <span className="font-medium">
                {llmStatusQuery.isLoading
                  ? "Checking local model runtime..."
                  : llmStatus?.running
                  ? `${llmStatus.provider} is running`
                  : `${llmStatus?.provider ?? "Local model runtime"} is not reachable`}
              </span>
            </div>
            {!llmStatusQuery.isLoading && !llmStatus?.running && (
              <p className="text-xs text-slate-500">
                Start Ollama locally (e.g. <code>ollama serve</code>) to enable chat answers.
              </p>
            )}
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">Chat model</label>
              <select
                value={activeModel}
                onChange={(event) => onSelectModel(event.target.value)}
                disabled={!llmStatus?.running || !llmStatus.models.length}
                className="h-9 w-full rounded-md border border-line bg-white px-2 text-sm focus:border-brand focus:outline-none disabled:opacity-60"
              >
                {llmStatus?.running && llmStatus.models.length ? (
                  llmStatus.models.map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))
                ) : (
                  <option value="">No models available</option>
                )}
              </select>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-lg font-semibold">{value}</div>
      <div className="text-slate-500">{label}</div>
    </div>
  );
}

