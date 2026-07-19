import { AlertCircle, BookmarkPlus, Check, Copy, RefreshCw, Send, Trash2, X } from "lucide-react";
import { FormEvent, useState, useEffect, useRef } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";

type ChatResponse = {
  answer: string;
  sources: Array<{ document_name: string; page_number: number | null; score: number; text?: string }>;
  conversation_id: number;
  message_id: number;
};

type ChatMessage = {
  id?: number;
  role: string;
  content: string;
  sources?: ChatResponse["sources"];
};

type LlmStatus = {
  provider: string;
  default_model: string;
  running: boolean;
  models: string[];
};

const CAN_MANAGE_KNOWLEDGE_BASE = new Set(["admin", "knowledge_manager"]);

export function ChatAssistant({
  token,
  role,
  selectedModel,
  onSelectModel
}: {
  token: string;
  role: string;
  selectedModel: string;
  onSelectModel: (model: string) => void;
}) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [isPending, setIsPending] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState<string>("All");
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [regeneratingId, setRegeneratingId] = useState<number | null>(null);
  const [savingMessage, setSavingMessage] = useState<{ id: number; content: string } | null>(null);
  const [saveTitle, setSaveTitle] = useState("");
  const [saveCategory, setSaveCategory] = useState("General");
  const [saveError, setSaveError] = useState("");
  const [savedId, setSavedId] = useState<number | null>(null);
  const messageEndRef = useRef<HTMLDivElement>(null);

  const canManageKnowledgeBase = CAN_MANAGE_KNOWLEDGE_BASE.has(role);

  const categoriesQuery = useQuery({
    queryKey: ["categories"],
    queryFn: () => api<Array<{ id: number; name: string; description: string | null }>>("/categories", token)
  });

  const llmStatusQuery = useQuery({
    queryKey: ["llm-status"],
    queryFn: () => api<LlmStatus>("/chat/models", token),
    refetchInterval: 15000
  });

  const llmStatus = llmStatusQuery.data;
  const activeModel = selectedModel || llmStatus?.default_model || "";

  // Auto scroll to bottom of chat
  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isPending]);

  const historyQuery = useQuery({
    queryKey: ["chat-history"],
    queryFn: () =>
      api<
        Array<{
          id: number;
          title: string;
          messages: ChatMessage[];
        }>
      >("/chat/history", token)
  });

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!question.trim()) return;
    const current = question;
    setQuestion("");
    setMessages((items) => [...items, { role: "user", content: current }]);
    setIsPending(true);
    try {
      const response = await api<ChatResponse>("/chat/query", token, {
        method: "POST",
        body: JSON.stringify({
          question: current,
          conversation_id: conversationId,
          category: categoryFilter === "All" ? null : categoryFilter,
          model: activeModel || null
        })
      });
      setConversationId(response.conversation_id);
      setMessages((items) => [
        ...items,
        { id: response.message_id, role: "assistant", content: response.answer, sources: response.sources }
      ]);
      historyQuery.refetch();
    } catch (error) {
      setMessages((items) => [
        ...items,
        {
          role: "assistant",
          content: "An error occurred while communicating with the assistant. Make sure the backend and local model runtime (Ollama) are active."
        }
      ]);
    } finally {
      setIsPending(false);
    }
  }

  const deleteChatMutation = useMutation({
    mutationFn: async (id: number) => {
      const response = await fetch(`/api/chat/conversations/${id}`, {
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
    onSuccess: (_, id) => {
      historyQuery.refetch();
      if (conversationId === id) {
        setConversationId(null);
        setMessages([]);
      }
    }
  });

  const regenerateMutation = useMutation({
    mutationFn: async (messageId: number) =>
      api<ChatResponse>("/chat/regenerate", token, {
        method: "POST",
        body: JSON.stringify({
          message_id: messageId,
          category: categoryFilter === "All" ? null : categoryFilter,
          model: activeModel || null
        })
      }),
    onMutate: (messageId: number) => {
      setRegeneratingId(messageId);
    },
    onSuccess: (response, messageId) => {
      setMessages((items) =>
        items.map((message) =>
          message.id === messageId
            ? { ...message, content: response.answer, sources: response.sources }
            : message
        )
      );
      historyQuery.refetch();
    },
    onSettled: () => {
      setRegeneratingId(null);
    }
  });

  const addToKnowledgeBaseMutation = useMutation({
    mutationFn: async (payload: { title: string; content: string; category: string | null }) =>
      api<{ id: number; status: string }>("/documents/from-text", token, {
        method: "POST",
        body: JSON.stringify(payload)
      }),
    onSuccess: () => {
      const savedMessageId = savingMessage?.id ?? null;
      setSavingMessage(null);
      setSaveError("");
      setSavedId(savedMessageId);
      setTimeout(() => setSavedId((current) => (current === savedMessageId ? null : current)), 2500);
    },
    onError: (error: unknown) => {
      setSaveError(error instanceof Error ? error.message : "Failed to save to knowledge base.");
    }
  });

  async function copyMessage(index: number, content: string) {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex((current) => (current === index ? null : current)), 1500);
    } catch {
      // Clipboard access can be denied by the browser - nothing useful to recover here.
    }
  }

  function openSaveModal(message: ChatMessage) {
    if (message.id === undefined) return;
    setSavingMessage({ id: message.id, content: message.content });
    setSaveTitle(`Chat response - ${new Date().toLocaleString()}`);
    setSaveCategory(categoriesQuery.data?.[0]?.name ?? "General");
    setSaveError("");
  }

  const startNewChat = () => {
    setConversationId(null);
    setMessages([]);
  };

  const loadSession = (session: { id: number; title: string; messages: ChatMessage[] }) => {
    setConversationId(session.id);
    setMessages(session.messages);
  };

  return (
    <>
      <PageHeader title="Chat Assistant" subtitle="Ask grounded questions and review every source used in the answer." />
      <div className="grid grid-cols-[250px_1fr] h-[calc(100vh-180px)] rounded-md border border-line bg-white overflow-hidden">
        <aside className="border-r border-line bg-slate-50 flex flex-col h-full min-h-0">
          <div className="p-3 border-b border-line">
            <button
              onClick={startNewChat}
              className="w-full flex h-10 items-center justify-center gap-2 rounded-md border border-line bg-white text-sm font-medium hover:bg-slate-100 transition"
            >
              + New Chat
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {(historyQuery.data ?? []).map((session) => (
              <div
                key={session.id}
                className={`group flex items-center justify-between px-2 py-1.5 rounded-md transition ${
                  conversationId === session.id
                    ? "bg-slate-200 text-slate-800 font-semibold"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                <button
                  onClick={() => loadSession(session)}
                  className="flex-1 text-left text-xs truncate"
                >
                  {session.title || "KnowledgeHub chat"}
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm("Are you sure you want to delete this chat session?")) {
                      deleteChatMutation.mutate(session.id);
                    }
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-red-500 transition"
                  title="Delete chat session"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
          </div>
        </aside>

        <section className="flex flex-col h-full bg-white min-h-0">
          <div className="flex items-center justify-between border-b border-line px-4 py-2 bg-slate-50/50">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-slate-500">Filter Grounding Source:</span>
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                disabled={categoriesQuery.isLoading}
                className="h-8 rounded-md border border-line bg-white px-2 py-1 text-xs text-slate-800 focus:border-brand focus:outline-none disabled:opacity-60"
              >
                <option value="All">All Categories</option>
                {(categoriesQuery.data ?? []).map((cat) => (
                  <option key={cat.id} value={cat.name}>{cat.name}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2" title={llmStatus?.running ? "Local model runtime is running" : "Local model runtime is not reachable"}>
              <span className={`h-1.5 w-1.5 rounded-full ${llmStatus?.running ? "bg-emerald-500" : "bg-red-500"}`} />
              <span className="text-xs font-medium text-slate-500">Model:</span>
              <select
                value={activeModel}
                onChange={(e) => onSelectModel(e.target.value)}
                disabled={!llmStatus?.running || !llmStatus.models.length}
                className="h-8 rounded-md border border-line bg-white px-2 py-1 text-xs text-slate-800 focus:border-brand focus:outline-none disabled:opacity-60"
              >
                {llmStatus?.running && llmStatus.models.length ? (
                  llmStatus.models.map((model) => (
                    <option key={model} value={model}>{model}</option>
                  ))
                ) : (
                  <option value="">Unavailable</option>
                )}
              </select>
            </div>
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto p-4">
            {messages.length === 0 && (
              <div className="flex h-full items-center justify-center text-sm text-slate-400">
                Start typing to begin a new grounded conversation.
              </div>
            )}
            {messages.map((message, index) => (
              <div
                key={index}
                className={
                  message.role === "user"
                    ? "ml-auto max-w-2xl rounded-md bg-brand p-3 text-white"
                    : "max-w-3xl rounded-md bg-slate-100 p-3 mr-auto"
                }
              >
                <p className="whitespace-pre-wrap text-sm leading-6">{message.content}</p>
                {message.sources?.length ? (
                  <div className="mt-3 border-t border-slate-200/60 pt-2 text-xs">
                    <span className="font-semibold text-slate-500 block mb-1.5">Grounded Sources:</span>
                    <div className="flex flex-wrap gap-2">
                      {message.sources.map((source, sIdx) => (
                        <div key={sIdx} className="group relative">
                          <span className="inline-flex items-center gap-1 rounded bg-slate-200/70 hover:bg-slate-200 px-2 py-1 text-xs font-medium text-slate-700 cursor-help transition">
                            <span className="truncate max-w-[150px]">{source.document_name}</span>
                            {source.page_number && <span className="opacity-60 text-[10px]">p.{source.page_number}</span>}
                            <span className="text-[10px] text-brand opacity-80">({Math.round(source.score * 100)}%)</span>
                          </span>
                          {/* Tooltip / Hover Snippet Card */}
                          {source.text && (
                            <div className="absolute bottom-full left-0 mb-2 w-80 scale-95 opacity-0 pointer-events-none group-hover:scale-100 group-hover:opacity-100 group-hover:pointer-events-auto origin-bottom-left transition-all duration-200 ease-out z-30">
                              <div className="rounded-lg border border-line bg-white p-3 shadow-xl">
                                <div className="text-[10px] font-semibold text-brand mb-1 flex justify-between">
                                  <span>Snippet from {source.document_name}</span>
                                  <span>Score: {Math.round(source.score * 100)}%</span>
                                </div>
                                <p className="text-[11px] text-slate-600 leading-normal max-h-32 overflow-y-auto whitespace-pre-wrap">
                                  {source.text}
                                </p>
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
                {message.role === "assistant" && (
                  <div className="mt-2 flex items-center gap-1 border-t border-slate-200/60 pt-2">
                    <button
                      onClick={() => copyMessage(index, message.content)}
                      title="Copy response"
                      className="flex items-center gap-1 rounded px-1.5 py-1 text-[11px] font-medium text-slate-500 hover:bg-slate-200/70 hover:text-slate-700 transition"
                    >
                      {copiedIndex === index ? <Check size={12} className="text-emerald-600" /> : <Copy size={12} />}
                      {copiedIndex === index ? "Copied" : "Copy"}
                    </button>
                    {message.id !== undefined && (
                      <button
                        onClick={() => regenerateMutation.mutate(message.id!)}
                        disabled={regeneratingId === message.id}
                        title="Regenerate response"
                        className="flex items-center gap-1 rounded px-1.5 py-1 text-[11px] font-medium text-slate-500 hover:bg-slate-200/70 hover:text-slate-700 transition disabled:opacity-50"
                      >
                        <RefreshCw size={12} className={regeneratingId === message.id ? "animate-spin" : ""} />
                        {regeneratingId === message.id ? "Regenerating..." : "Regenerate"}
                      </button>
                    )}
                    {canManageKnowledgeBase && message.id !== undefined && (
                      <button
                        onClick={() => openSaveModal(message)}
                        title="Add this response to the knowledge base"
                        className="flex items-center gap-1 rounded px-1.5 py-1 text-[11px] font-medium text-slate-500 hover:bg-slate-200/70 hover:text-slate-700 transition"
                      >
                        {savedId === message.id ? <Check size={12} className="text-emerald-600" /> : <BookmarkPlus size={12} />}
                        {savedId === message.id ? "Saved" : "Add to Knowledge Base"}
                      </button>
                    )}
                  </div>
                )}
              </div>
            ))}
            {isPending && (
              <div className="max-w-3xl rounded-md bg-slate-100 p-3 mr-auto flex items-center gap-2">
                <span className="flex h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.3s]"></span>
                <span className="flex h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.15s]"></span>
                <span className="flex h-2 w-2 animate-bounce rounded-full bg-slate-400"></span>
                <span className="text-xs text-slate-500 ml-1">Thinking...</span>
              </div>
            )}
            <div ref={messageEndRef} />
          </div>
          <form onSubmit={submit} className="flex gap-2 border-t border-line p-3">
            <input
              className="h-11 flex-1 rounded-md border border-line px-3"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask about the knowledge base"
            />
            <button className="flex h-11 w-11 items-center justify-center rounded-md bg-brand text-white" title="Send">
              <Send size={18} />
            </button>
          </form>
        </section>
      </div>

      {savingMessage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-lg border border-line bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
                <BookmarkPlus size={18} className="text-brand" />
                Add to Knowledge Base
              </h3>
              <button
                onClick={() => setSavingMessage(null)}
                className="text-slate-400 hover:text-slate-600 transition"
              >
                <X size={18} />
              </button>
            </div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!saveTitle.trim()) {
                  setSaveError("Title is required.");
                  return;
                }
                addToKnowledgeBaseMutation.mutate({
                  title: saveTitle.trim(),
                  content: savingMessage.content,
                  category: saveCategory || null
                });
              }}
              className="space-y-4"
            >
              {saveError && (
                <div className="rounded bg-red-50 p-3 text-xs text-red-700 border border-red-200 flex items-start gap-1">
                  <AlertCircle size={14} className="shrink-0 mt-0.5" />
                  <span>{saveError}</span>
                </div>
              )}
              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1">Title</label>
                <input
                  type="text"
                  value={saveTitle}
                  onChange={(e) => setSaveTitle(e.target.value)}
                  className="w-full h-10 px-3 rounded border border-line text-sm focus:border-brand focus:outline-none"
                  placeholder="e.g. AdSense report summary"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1">Category</label>
                <select
                  value={saveCategory}
                  onChange={(e) => setSaveCategory(e.target.value)}
                  className="w-full h-10 px-2 rounded border border-line bg-white text-sm focus:border-brand focus:outline-none"
                >
                  {(categoriesQuery.data ?? []).map((cat) => (
                    <option key={cat.id} value={cat.name}>{cat.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1">Content preview</label>
                <p className="max-h-32 overflow-y-auto whitespace-pre-wrap rounded border border-line bg-slate-50 p-2 text-xs text-slate-600">
                  {savingMessage.content}
                </p>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setSavingMessage(null)}
                  className="h-10 px-4 rounded border border-line text-sm font-medium text-slate-600 hover:bg-slate-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addToKnowledgeBaseMutation.isPending}
                  className="flex h-10 items-center justify-center gap-2 rounded bg-brand px-4 text-sm font-medium text-white hover:bg-brand/90 disabled:opacity-60 transition"
                >
                  {addToKnowledgeBaseMutation.isPending ? "Saving..." : "Save to Knowledge Base"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
