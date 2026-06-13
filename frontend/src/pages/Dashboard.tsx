import { Database, FileCheck, Files, MessageSquare, Users } from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { StatTile } from "../components/StatTile";

export function Dashboard({ token }: { token: string }) {
  void token;
  return (
    <>
      <PageHeader title="Dashboard" subtitle="Operational overview for offline knowledge operations." />
      <div className="grid grid-cols-4 gap-4">
        <StatTile label="Total documents" value="0" icon={Files} />
        <StatTile label="Indexed documents" value="0" icon={FileCheck} />
        <StatTile label="Users" value="1" icon={Users} />
        <StatTile label="Queries today" value="0" icon={MessageSquare} />
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

