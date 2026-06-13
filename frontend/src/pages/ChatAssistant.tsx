import { Send } from "lucide-react";
import { FormEvent, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";

type ChatResponse = {
  answer: string;
  sources: Array<{ document_name: string; page_number: number | null; score: number }>;
  conversation_id: number;
};

export function ChatAssistant({ token }: { token: string }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Array<{ role: string; content: string; sources?: ChatResponse["sources"] }>>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [isPending, setIsPending] = useState(false);

  const historyQuery = useQuery({
    queryKey: ["chat-history"],
    queryFn: () =>
      api<
        Array<{
          id: number;
          title: string;
          messages: Array<{ role: string; content: string; sources?: ChatResponse["sources"] }>;
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
        body: JSON.stringify({ question: current, conversation_id: conversationId })
      });
      setConversationId(response.conversation_id);
      setMessages((items) => [...items, { role: "assistant", content: response.answer, sources: response.sources }]);
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

  const startNewChat = () => {
    setConversationId(null);
    setMessages([]);
  };

  const loadSession = (session: {
    id: number;
    title: string;
    messages: Array<{ role: string; content: string; sources?: ChatResponse["sources"] }>;
  }) => {
    setConversationId(session.id);
    setMessages(session.messages);
  };

  return (
    <>
      <PageHeader title="Chat Assistant" subtitle="Ask grounded questions and review every source used in the answer." />
      <div className="grid grid-cols-[250px_1fr] h-[calc(100vh-150px)] rounded-md border border-line bg-white overflow-hidden">
        <aside className="border-r border-line bg-slate-50 flex flex-col h-full">
          <div className="p-3 border-b border-line">
            <button
              onClick={startNewChat}
              className="w-full flex h-10 items-center justify-center gap-2 rounded-md border border-line bg-white text-sm font-medium hover:bg-slate-100 transition"
            >
              + New Chat
            </button>
          </div>
          <div className="flex-1 overflow-auto p-2 space-y-1">
            {(historyQuery.data ?? []).map((session) => (
              <button
                key={session.id}
                onClick={() => loadSession(session)}
                className={`w-full text-left px-3 py-2 rounded-md text-xs truncate transition ${
                  conversationId === session.id
                    ? "bg-slate-200 font-semibold text-slate-800"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                {session.title || "KnowledgeHub chat"}
              </button>
            ))}
          </div>
        </aside>

        <section className="flex flex-col h-full bg-white">
          <div className="flex-1 space-y-4 overflow-auto p-4">
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
                  <div className="mt-3 border-t border-line pt-2 text-xs text-slate-600">
                    Sources:{" "}
                    {message.sources
                      .map(
                        (source) =>
                          `${source.document_name}${source.page_number ? ` p.${source.page_number}` : ""}`
                      )
                      .join(", ")}
                  </div>
                ) : null}
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
    </>
  );
}

