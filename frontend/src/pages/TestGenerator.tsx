import { useRef, useState } from "react";
import {
  Upload,
  Loader2,
  AlertCircle,
  ClipboardList,
  ArrowLeft,
  Download,
  RefreshCw,
  Trash2,
  Sparkles
} from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";

type SessionSummary = {
  id: number;
  status: string;
  requirement_document_name: string | null;
  clarifying_round: number;
  created_at: string;
};

type Question = {
  id: number;
  round: number;
  question: string;
  answer: string | null;
  status: "pending" | "answered" | "skipped";
};

type TestCaseRow = {
  id: number;
  title: string;
  preconditions: string;
  steps: string[];
  expected_result: string;
  priority: string;
  case_type: string;
};

type ScenarioRow = {
  id: number;
  title: string;
  description: string;
  priority: string;
  test_cases: TestCaseRow[];
};

type SessionDetail = {
  id: number;
  status: string;
  clarifying_round: number;
  max_clarifying_rounds: number;
  error_message: string | null;
  context_category: string | null;
  requirement_document_name: string | null;
  assumptions: string[];
  questions: Question[];
  scenarios: ScenarioRow[];
};

const ACTIVE_STATUSES = new Set(["analyzing", "generating", "ready"]);

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    completed: "bg-emerald-50 text-emerald-700 ring-emerald-600/10",
    questions_pending: "bg-amber-50 text-amber-700 ring-amber-600/10",
    failed: "bg-red-50 text-red-700 ring-red-600/10"
  };
  const active = ACTIVE_STATUSES.has(status);
  const className = styles[status] || "bg-blue-50 text-blue-700 ring-blue-700/10";
  const label = status.replace(/_/g, " ");
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ring-1 ring-inset ${className}`}
    >
      {active && <Loader2 size={10} className="animate-spin" />}
      {label}
    </span>
  );
}

export function TestGenerator({ token }: { token: string }) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [contextCategory, setContextCategory] = useState<string>("");
  const [uploadingFileName, setUploadingFileName] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string>("");
  const [answers, setAnswers] = useState<Record<number, { text: string; skip: boolean }>>({});

  const categoriesQuery = useQuery({
    queryKey: ["categories"],
    queryFn: () => api<Array<{ id: number; name: string }>>("/categories", token)
  });

  const sessionsQuery = useQuery({
    queryKey: ["testgen-sessions"],
    queryFn: () => api<SessionSummary[]>("/testgen/sessions", token)
  });

  const detailQuery = useQuery({
    queryKey: ["testgen-session", selectedSessionId],
    queryFn: () => api<SessionDetail>(`/testgen/sessions/${selectedSessionId}`, token),
    enabled: selectedSessionId !== null,
    refetchInterval: (query) => (ACTIVE_STATUSES.has(query.state.data?.status ?? "") ? 2000 : false)
  });

  const createMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const uploadResponse = await fetch("/api/documents/upload", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      });
      if (!uploadResponse.ok) throw new Error(await uploadResponse.text());
      const uploaded: { id: number } = await uploadResponse.json();

      return api<{ id: number }>("/testgen/sessions", token, {
        method: "POST",
        body: JSON.stringify({
          requirement_document_id: uploaded.id,
          context_category: contextCategory || null
        })
      });
    },
    onSuccess: (result) => {
      setUploadingFileName(null);
      setUploadError("");
      queryClient.invalidateQueries({ queryKey: ["testgen-sessions"] });
      setSelectedSessionId(result.id);
    },
    onError: (err: any) => {
      setUploadingFileName(null);
      setUploadError(err.message || "Could not start test generation for this document.");
    }
  });

  const answersMutation = useMutation({
    mutationFn: () =>
      api(`/testgen/sessions/${selectedSessionId}/answers`, token, {
        method: "POST",
        body: JSON.stringify({
          answers: Object.entries(answers).map(([questionId, value]) => ({
            question_id: Number(questionId),
            answer: value.text,
            skip: value.skip
          }))
        })
      }),
    onSuccess: () => {
      setAnswers({});
      queryClient.invalidateQueries({ queryKey: ["testgen-session", selectedSessionId] });
    }
  });

  const generateMutation = useMutation({
    mutationFn: () => api(`/testgen/sessions/${selectedSessionId}/generate`, token, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["testgen-session", selectedSessionId] })
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api(`/testgen/sessions/${id}`, token, { method: "DELETE" }),
    onSuccess: () => {
      setSelectedSessionId(null);
      queryClient.invalidateQueries({ queryKey: ["testgen-sessions"] });
    }
  });

  const updateCaseMutation = useMutation({
    mutationFn: ({ caseId, patch }: { caseId: number; patch: Partial<TestCaseRow> }) =>
      api(`/testgen/cases/${caseId}`, token, { method: "PATCH", body: JSON.stringify(patch) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["testgen-session", selectedSessionId] })
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadingFileName(file.name);
      createMutation.mutate(file);
    }
    e.target.value = "";
  };

  const handleExport = () => {
    if (!selectedSessionId) return;
    fetch(`/api/testgen/sessions/${selectedSessionId}/export.csv`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then((response) => response.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = `test-cases-session-${selectedSessionId}.csv`;
        anchor.click();
        URL.revokeObjectURL(url);
      });
  };

  if (selectedSessionId !== null) {
    const detail = detailQuery.data;
    const currentRoundQuestions = detail?.questions.filter(
      (question) => question.round === detail.clarifying_round && question.status === "pending"
    );

    return (
      <>
        <PageHeader
          title={detail?.requirement_document_name || "Test Generation Session"}
          subtitle="Review clarifying questions and generated test scenarios for this requirement."
        />
        <button
          onClick={() => setSelectedSessionId(null)}
          className="mb-4 flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-900"
        >
          <ArrowLeft size={16} /> Back to sessions
        </button>

        {detailQuery.isLoading && <Loader2 className="animate-spin text-brand" />}

        {detail && (
          <div className="space-y-5">
            <div className="flex items-center justify-between rounded-md border border-line bg-white p-4">
              <StatusBadge status={detail.status} />
              <div className="flex gap-2">
                <button
                  onClick={() => generateMutation.mutate()}
                  disabled={detail.status === "generating" || generateMutation.isPending}
                  className="flex items-center gap-2 rounded-md border border-line px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  {detail.status === "failed" || detail.status === "completed" ? (
                    <RefreshCw size={15} />
                  ) : (
                    <Sparkles size={15} />
                  )}
                  {detail.status === "failed" || detail.status === "completed"
                    ? "Regenerate"
                    : "Generate now (skip remaining questions)"}
                </button>
                {detail.status === "completed" && (
                  <button
                    onClick={handleExport}
                    className="flex items-center gap-2 rounded-md bg-brand px-3 py-2 text-sm font-medium text-white hover:bg-brand/90"
                  >
                    <Download size={15} /> Export CSV
                  </button>
                )}
                <button
                  onClick={() => {
                    if (confirm("Delete this test generation session?")) deleteMutation.mutate(detail.id);
                  }}
                  className="flex items-center gap-2 rounded-md border border-line px-3 py-2 text-sm text-red-600 hover:bg-red-50"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            </div>

            {detail.error_message && (
              <div className="rounded-md bg-red-50 p-4 border border-red-200 flex gap-2 text-sm text-red-700">
                <AlertCircle size={18} className="shrink-0 mt-0.5" />
                <span>{detail.error_message}</span>
              </div>
            )}

            {detail.status === "questions_pending" && currentRoundQuestions && (
              <div className="rounded-md border border-line bg-white p-5 space-y-4">
                <p className="text-sm font-semibold text-slate-700">
                  Round {detail.clarifying_round} of {detail.max_clarifying_rounds} - the assistant needs more
                  context about your app to write accurate tests.
                </p>
                {currentRoundQuestions.map((question) => (
                  <div key={question.id} className="space-y-1.5">
                    <label className="block text-sm text-slate-700">{question.question}</label>
                    <textarea
                      className="w-full rounded border border-line p-2 text-sm focus:border-brand focus:outline-none"
                      rows={2}
                      placeholder="Your answer..."
                      value={answers[question.id]?.text ?? ""}
                      onChange={(e) =>
                        setAnswers((prev) => ({
                          ...prev,
                          [question.id]: { text: e.target.value, skip: false }
                        }))
                      }
                    />
                  </div>
                ))}
                <button
                  onClick={() => answersMutation.mutate()}
                  disabled={answersMutation.isPending}
                  className="flex items-center gap-2 rounded-md bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand/90 disabled:opacity-55"
                >
                  {answersMutation.isPending && <Loader2 size={15} className="animate-spin" />}
                  Submit answers
                </button>
              </div>
            )}

            {(detail.status === "analyzing" || detail.status === "generating" || detail.status === "ready") && (
              <div className="flex items-center gap-3 rounded-md border border-line bg-white p-6 text-sm text-slate-600">
                <Loader2 size={18} className="animate-spin text-brand" />
                {detail.status === "analyzing"
                  ? "Analyzing the requirement and gathering related knowledge base context..."
                  : "Generating test scenarios and test cases..."}
              </div>
            )}

            {detail.status === "completed" && (
              <>
                {detail.assumptions.length > 0 && (
                  <div className="rounded-md bg-amber-50 border border-amber-200 p-4 text-sm text-amber-800">
                    <p className="font-semibold mb-1">Assumptions made</p>
                    <ul className="list-disc list-inside space-y-0.5">
                      {detail.assumptions.map((assumption, index) => (
                        <li key={index}>{assumption}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {detail.scenarios.map((scenario) => (
                  <div key={scenario.id} className="rounded-md border border-line bg-white overflow-hidden">
                    <div className="border-b border-line bg-slate-50 px-4 py-3">
                      <h3 className="text-sm font-semibold text-slate-800">{scenario.title}</h3>
                      <p className="text-xs text-slate-500 mt-0.5">{scenario.description}</p>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-50 text-slate-500">
                          <tr>
                            <th className="px-3 py-2">Test Case</th>
                            <th className="px-3 py-2">Preconditions</th>
                            <th className="px-3 py-2">Steps</th>
                            <th className="px-3 py-2">Expected Result</th>
                            <th className="px-3 py-2">Priority</th>
                            <th className="px-3 py-2">Type</th>
                          </tr>
                        </thead>
                        <tbody>
                          {scenario.test_cases.map((testCase) => (
                            <tr key={testCase.id} className="border-t border-line align-top">
                              <td className="px-3 py-2 min-w-[160px]">
                                <textarea
                                  defaultValue={testCase.title}
                                  className="w-full resize-y rounded border border-transparent p-1 hover:border-line focus:border-brand focus:outline-none"
                                  onBlur={(e) =>
                                    updateCaseMutation.mutate({ caseId: testCase.id, patch: { title: e.target.value } })
                                  }
                                />
                              </td>
                              <td className="px-3 py-2 min-w-[160px]">
                                <textarea
                                  defaultValue={testCase.preconditions}
                                  className="w-full resize-y rounded border border-transparent p-1 hover:border-line focus:border-brand focus:outline-none"
                                  onBlur={(e) =>
                                    updateCaseMutation.mutate({
                                      caseId: testCase.id,
                                      patch: { preconditions: e.target.value }
                                    })
                                  }
                                />
                              </td>
                              <td className="px-3 py-2 min-w-[220px]">
                                <textarea
                                  defaultValue={testCase.steps.join("\n")}
                                  rows={Math.max(2, testCase.steps.length)}
                                  className="w-full resize-y rounded border border-transparent p-1 hover:border-line focus:border-brand focus:outline-none"
                                  onBlur={(e) =>
                                    updateCaseMutation.mutate({
                                      caseId: testCase.id,
                                      patch: { steps: e.target.value.split("\n").filter((line) => line.trim()) }
                                    })
                                  }
                                />
                              </td>
                              <td className="px-3 py-2 min-w-[160px]">
                                <textarea
                                  defaultValue={testCase.expected_result}
                                  className="w-full resize-y rounded border border-transparent p-1 hover:border-line focus:border-brand focus:outline-none"
                                  onBlur={(e) =>
                                    updateCaseMutation.mutate({
                                      caseId: testCase.id,
                                      patch: { expected_result: e.target.value }
                                    })
                                  }
                                />
                              </td>
                              <td className="px-3 py-2 capitalize">{testCase.priority}</td>
                              <td className="px-3 py-2 capitalize">{testCase.case_type}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))}
              </>
            )}
          </div>
        )}
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Test Generator"
        subtitle="Upload a requirement document and generate grounded test scenarios and test cases."
      />

      {uploadError && (
        <div className="mb-4 rounded-md bg-red-50 p-4 border border-red-200 flex gap-2 text-sm text-red-700">
          <AlertCircle size={18} className="shrink-0 mt-0.5" />
          <span>{uploadError}</span>
        </div>
      )}

      <div className="mb-5 flex flex-wrap items-center justify-end gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-500">Extra context category:</span>
          <select
            value={contextCategory}
            onChange={(e) => setContextCategory(e.target.value)}
            disabled={createMutation.isPending}
            className="h-10 rounded-md border border-line bg-white px-3 py-1.5 text-sm text-slate-800 focus:border-brand focus:outline-none disabled:opacity-50"
          >
            <option value="">All categories</option>
            {(categoriesQuery.data ?? []).map((cat) => (
              <option key={cat.id} value={cat.name}>
                {cat.name}
              </option>
            ))}
          </select>
        </div>
        <input type="file" ref={fileInputRef} onChange={handleFileChange} className="hidden" accept=".pdf,.docx,.txt,.md,.csv" />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={createMutation.isPending}
          className="flex h-10 items-center gap-2 rounded-md bg-brand px-4 text-sm font-medium text-white hover:bg-brand/90 disabled:opacity-55 transition"
        >
          {createMutation.isPending ? <Loader2 size={17} className="animate-spin" /> : <Upload size={17} />}
          {createMutation.isPending ? "Uploading..." : "Upload requirement doc"}
        </button>
      </div>

      <div className="overflow-hidden rounded-md border border-line bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="px-4 py-3">Requirement Document</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Clarifying Round</th>
              <th className="px-4 py-3">Created</th>
            </tr>
          </thead>
          <tbody>
            {uploadingFileName && (
              <tr className="border-t border-line bg-slate-50/50 animate-pulse">
                <td className="px-4 py-3 font-medium text-slate-500 flex items-center gap-2">
                  <Loader2 size={15} className="animate-spin text-brand" />
                  {uploadingFileName}
                </td>
                <td className="px-4 py-3 text-slate-400" colSpan={3}>
                  Starting analysis...
                </td>
              </tr>
            )}
            {(sessionsQuery.data ?? []).map((row) => (
              <tr
                key={row.id}
                className="border-t border-line cursor-pointer hover:bg-slate-50"
                onClick={() => setSelectedSessionId(row.id)}
              >
                <td className="px-4 py-3 font-medium flex items-center gap-2">
                  <ClipboardList size={16} className="text-slate-400 shrink-0" />
                  {row.requirement_document_name}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={row.status} />
                </td>
                <td className="px-4 py-3">{row.clarifying_round}</td>
                <td className="px-4 py-3">{new Date(row.created_at).toLocaleString()}</td>
              </tr>
            ))}
            {!uploadingFileName && (sessionsQuery.data ?? []).length === 0 && (
              <tr className="border-t border-line">
                <td colSpan={4} className="px-4 py-8 text-center text-slate-400">
                  No test generation sessions yet. Upload a requirement document to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
