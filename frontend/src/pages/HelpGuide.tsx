import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { AlertCircle, Loader2 } from "lucide-react";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";

export function HelpGuide({ token }: { token: string }) {
  const guideQuery = useQuery({
    queryKey: ["help-guide"],
    queryFn: () => api<{ content: string }>("/help/guide", token)
  });

  const components: Components = useMemo(
    () => ({
      h1: (props) => <h1 className="mt-8 mb-3 text-2xl font-semibold text-slate-900 first:mt-0" {...props} />,
      h2: (props) => (
        <h2 className="mt-8 mb-3 border-b border-line pb-2 text-xl font-semibold text-slate-900" {...props} />
      ),
      h3: (props) => <h3 className="mt-6 mb-2 text-base font-semibold text-slate-800" {...props} />,
      p: (props) => <p className="mb-3 text-sm leading-6 text-slate-700" {...props} />,
      a: (props) => (
        <a className="text-brand underline hover:text-brand/80" target="_blank" rel="noopener noreferrer" {...props} />
      ),
      ul: (props) => <ul className="mb-3 list-disc space-y-1 pl-5 text-sm text-slate-700" {...props} />,
      ol: (props) => <ol className="mb-3 list-decimal space-y-1 pl-5 text-sm text-slate-700" {...props} />,
      code: (props) => <code className="rounded bg-slate-100 px-1 py-0.5 text-xs text-slate-800" {...props} />,
      pre: (props) => (
        <pre
          className="mb-3 overflow-x-auto rounded-md border border-line bg-slate-50 p-3 text-xs text-slate-800 [&>code]:bg-transparent [&>code]:p-0"
          {...props}
        />
      ),
      table: (props) => (
        <div className="mb-3 overflow-x-auto rounded-md border border-line">
          <table className="w-full text-left text-sm" {...props} />
        </div>
      ),
      thead: (props) => <thead className="bg-slate-50 text-slate-600" {...props} />,
      th: (props) => <th className="px-3 py-2 font-semibold" {...props} />,
      td: (props) => <td className="border-t border-line px-3 py-2 align-top" {...props} />,
      hr: () => <hr className="my-6 border-line" />
    }),
    []
  );

  return (
    <>
      <PageHeader
        title="Help Guide"
        subtitle="Features, architecture, setup, and configuration reference for KnowledgeHub AI."
      />
      {guideQuery.isLoading && (
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Loader2 size={16} className="animate-spin" /> Loading guide...
        </div>
      )}
      {guideQuery.isError && (
        <div className="flex items-center gap-2 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <AlertCircle size={16} /> Could not load the help guide.
        </div>
      )}
      {guideQuery.data && (
        <div className="rounded-md border border-line bg-white p-6">
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
            {guideQuery.data.content}
          </ReactMarkdown>
        </div>
      )}
    </>
  );
}
