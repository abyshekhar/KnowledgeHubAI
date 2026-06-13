import type { LucideIcon } from "lucide-react";

export function StatTile({ label, value, icon: Icon }: { label: string; value: string; icon: LucideIcon }) {
  return (
    <div className="rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex h-8 w-8 items-center justify-center rounded-md bg-slate-100 text-brand">
        <Icon size={18} />
      </div>
      <div className="text-2xl font-semibold">{value}</div>
      <div className="text-sm text-slate-500">{label}</div>
    </div>
  );
}

