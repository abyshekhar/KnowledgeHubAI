import { Upload } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";

type DocumentRow = {
  id: number;
  name: string;
  document_type: string;
  status: string;
  access_level: string;
};

export function KnowledgeBase({ token }: { token: string }) {
  const documents = useQuery({
    queryKey: ["documents"],
    queryFn: () => api<DocumentRow[]>("/documents", token)
  });

  return (
    <>
      <PageHeader title="Knowledge Base" subtitle="Upload, organize, index, and govern internal documents." />
      <div className="mb-4 flex justify-end">
        <button className="flex h-10 items-center gap-2 rounded-md bg-brand px-4 text-sm font-medium text-white">
          <Upload size={17} />
          Upload
        </button>
      </div>
      <div className="overflow-hidden rounded-md border border-line bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="px-4 py-3">Document</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Access</th>
            </tr>
          </thead>
          <tbody>
            {(documents.data ?? []).map((document) => (
              <tr key={document.id} className="border-t border-line">
                <td className="px-4 py-3 font-medium">{document.name}</td>
                <td className="px-4 py-3">{document.document_type}</td>
                <td className="px-4 py-3">{document.status}</td>
                <td className="px-4 py-3">{document.access_level}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

