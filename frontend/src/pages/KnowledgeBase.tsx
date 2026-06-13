import { useRef } from "react";
import { Upload, Trash2 } from "lucide-react";
import { useQuery, useMutation } from "@tanstack/react-query";
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
  const fileInputRef = useRef<HTMLInputElement>(null);

  const documents = useQuery({
    queryKey: ["documents"],
    queryFn: () => api<DocumentRow[]>("/documents", token)
  });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      
      const response = await fetch("/api/documents/upload", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`
        },
        body: formData
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      return response.json();
    },
    onSuccess: () => {
      documents.refetch();
    }
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      const response = await fetch(`/api/documents/${id}`, {
        method: "DELETE",
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      return response.json();
    },
    onSuccess: () => {
      documents.refetch();
    }
  });

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      uploadMutation.mutate(file);
    }
  };

  return (
    <>
      <PageHeader title="Knowledge Base" subtitle="Upload, organize, index, and govern internal documents." />
      <div className="mb-4 flex justify-end gap-3 items-center">
        {uploadMutation.isPending && (
          <span className="text-sm text-slate-500">Uploading...</span>
        )}
        {uploadMutation.isError && (
          <span className="text-sm text-red-500">Upload failed.</span>
        )}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          className="hidden"
          accept=".pdf,.docx,.txt,.md"
        />
        <button
          onClick={handleUploadClick}
          disabled={uploadMutation.isPending}
          className="flex h-10 items-center gap-2 rounded-md bg-brand px-4 text-sm font-medium text-white hover:bg-brand/90 disabled:opacity-55"
        >
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
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {(documents.data ?? []).map((document) => (
              <tr key={document.id} className="border-t border-line">
                <td className="px-4 py-3 font-medium">{document.name}</td>
                <td className="px-4 py-3">{document.document_type}</td>
                <td className="px-4 py-3">{document.status}</td>
                <td className="px-4 py-3">{document.access_level}</td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => {
                      if (confirm(`Are you sure you want to delete "${document.name}"?`)) {
                        deleteMutation.mutate(document.id);
                      }
                    }}
                    className="text-red-500 hover:text-red-700"
                    title="Delete document"
                  >
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

