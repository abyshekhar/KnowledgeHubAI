import { Database, FileCheck, Files, MessageSquare, Users } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { StatTile } from "../components/StatTile";

export function Dashboard({ token }: { token: string }) {
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
          <div className="border-b border-line px-4 py-3 font-medium">Runtime</div>
          <div className="flex items-center gap-3 p-4 text-sm">
            <Database className="text-brand" size={18} />
            SQLite + FAISS + Ollama
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

