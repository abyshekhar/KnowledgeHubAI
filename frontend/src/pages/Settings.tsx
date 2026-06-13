import { PageHeader } from "../components/PageHeader";

const rows = [
  ["LLM provider", "ollama"],
  ["Default model", "mistral"],
  ["Embedding model", "BAAI/bge-small-en-v1.5"],
  ["Vector store", "faiss"],
  ["Database", "sqlite"]
];

export function Settings() {
  return (
    <>
      <PageHeader title="Settings" subtitle="Configuration-driven runtime choices for offline deployments." />
      <div className="rounded-md border border-line bg-white">
        {rows.map(([label, value]) => (
          <div key={label} className="grid grid-cols-[240px_1fr] border-b border-line px-4 py-3 text-sm last:border-b-0">
            <span className="font-medium">{label}</span>
            <code className="text-slate-700">{value}</code>
          </div>
        ))}
      </div>
    </>
  );
}

