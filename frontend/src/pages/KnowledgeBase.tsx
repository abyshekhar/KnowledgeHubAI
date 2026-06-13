import { useRef, useState, useEffect } from "react";
import { Upload, Trash2, Loader2, AlertCircle } from "lucide-react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";

type DocumentRow = {
  id: number;
  name: string;
  document_type: string;
  status: string;
  access_level: string;
  category?: string;
};

export function KnowledgeBase({ token }: { token: string }) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadingFileName, setUploadingFileName] = useState<string | null>(null);
  const [uploadCategory, setUploadCategory] = useState<string>("General");

  const categoriesQuery = useQuery({
    queryKey: ["categories"],
    queryFn: () => api<Array<{ id: number; name: string; description: string | null }>>("/categories", token)
  });

  useEffect(() => {
    if (categoriesQuery.data && categoriesQuery.data.length > 0) {
      setUploadCategory(categoriesQuery.data[0].name);
    }
  }, [categoriesQuery.data]);

  const documents = useQuery({
    queryKey: ["documents"],
    queryFn: () => api<DocumentRow[]>("/documents", token),
    refetchInterval: (query) => {
      const data = query.state.data;
      const hasPending = data?.some(
        (doc) => doc.status === "pending" || doc.status === "processing"
      );
      return hasPending ? 2000 : false;
    }
  });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      
      const response = await fetch(`/api/documents/upload?category=${encodeURIComponent(uploadCategory)}`, {
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
      setUploadingFileName(null);
      documents.refetch();
    },
    onError: () => {
      setUploadingFileName(null);
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
    uploadMutation.reset();
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadingFileName(file.name);
      uploadMutation.mutate(file);
    }
    e.target.value = "";
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case "indexed":
        return (
          <span className="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-600/10">
            Indexed
          </span>
        );
      case "pending":
      case "processing":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700 ring-1 ring-inset ring-blue-700/10 animate-pulse">
            <Loader2 size={10} className="animate-spin text-blue-500" />
            Indexing...
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-semibold text-red-700 ring-1 ring-inset ring-red-600/10">
            Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center rounded-full bg-slate-50 px-2.5 py-0.5 text-xs font-semibold text-slate-600 ring-1 ring-inset ring-slate-500/10">
            {status}
          </span>
        );
    }
  };

  return (
    <>
      <PageHeader title="Knowledge Base" subtitle="Upload, organize, index, and govern internal documents." />
      
      {uploadMutation.isError && (
        <div className="mb-4 rounded-md bg-red-50 p-4 border border-red-200 flex justify-between items-start">
          <div className="flex gap-2 text-sm text-red-700">
            <AlertCircle size={18} className="shrink-0 mt-0.5" />
            <div>
              <strong className="font-semibold">Upload failed:</strong>
              <p className="mt-1 text-xs text-red-600 whitespace-pre-wrap">
                {uploadMutation.error?.message || "An error occurred during file upload."}
              </p>
            </div>
          </div>
          <button 
            onClick={() => uploadMutation.reset()}
            className="text-xs font-semibold text-red-800 hover:text-red-950 underline px-2 py-1"
          >
            Dismiss
          </button>
        </div>
      )}

      <div className="mb-4 flex justify-end gap-3 items-center">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-500">Category:</span>
          <select
            value={uploadCategory}
            onChange={(e) => setUploadCategory(e.target.value)}
            disabled={uploadMutation.isPending || categoriesQuery.isLoading}
            className="h-10 rounded-md border border-line bg-white px-3 py-1.5 text-sm text-slate-800 focus:border-brand focus:outline-none disabled:opacity-50"
          >
            {(categoriesQuery.data ?? []).map((cat) => (
              <option key={cat.id} value={cat.name}>{cat.name}</option>
            ))}
          </select>
        </div>
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
          className="flex h-10 items-center gap-2 rounded-md bg-brand px-4 text-sm font-medium text-white hover:bg-brand/90 disabled:opacity-55 transition"
        >
          {uploadMutation.isPending ? (
            <Loader2 size={17} className="animate-spin" />
          ) : (
            <Upload size={17} />
          )}
          {uploadMutation.isPending ? "Uploading..." : "Upload"}
        </button>
      </div>

      <div className="overflow-hidden rounded-md border border-line bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="px-4 py-3">Document</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Access</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {uploadingFileName && (
              <tr className="border-t border-line bg-slate-50/50 animate-pulse">
                <td className="px-4 py-3 font-medium text-slate-500 flex items-center gap-2">
                  <Loader2 size={15} className="animate-spin text-brand" />
                  <span className="truncate max-w-xs">{uploadingFileName}</span>
                </td>
                <td className="px-4 py-3 text-slate-400">
                  {uploadingFileName.split(".").pop()?.toUpperCase() || "-"}
                </td>
                <td className="px-4 py-3 text-slate-400">
                  {uploadCategory}
                </td>
                <td className="px-4 py-3">
                  <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700 ring-1 ring-inset ring-blue-700/10">
                    <Loader2 size={10} className="animate-spin text-blue-500" />
                    Uploading...
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-400">-</td>
                <td className="px-4 py-3 text-right text-slate-400">-</td>
              </tr>
            )}
            
            {(documents.data ?? []).map((document) => (
              <tr key={document.id} className="border-t border-line">
                <td className="px-4 py-3 font-medium">{document.name}</td>
                <td className="px-4 py-3 uppercase">{document.document_type}</td>
                <td className="px-4 py-3">{document.category || "General"}</td>
                <td className="px-4 py-3">{getStatusBadge(document.status)}</td>
                <td className="px-4 py-3">{document.access_level}</td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => {
                      if (confirm(`Are you sure you want to delete "${document.name}"?`)) {
                        deleteMutation.mutate(document.id);
                      }
                    }}
                    className="text-red-500 hover:text-red-700 p-1"
                    title="Delete document"
                  >
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
            
            {!uploadingFileName && (documents.data ?? []).length === 0 && (
              <tr className="border-t border-line">
                <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                  No documents found. Click the Upload button to add files.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}

