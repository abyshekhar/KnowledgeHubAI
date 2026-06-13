import { Send } from "lucide-react";
import { FormEvent, useState } from "react";
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

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!question.trim()) return;
    const current = question;
    setQuestion("");
    setMessages((items) => [...items, { role: "user", content: current }]);
    try {
      const response = await api<ChatResponse>("/chat/query", token, {
        method: "POST",
        body: JSON.stringify({ question: current, conversation_id: conversationId })
      });
      setConversationId(response.conversation_id);
      setMessages((items) => [...items, { role: "assistant", content: response.answer, sources: response.sources }]);
    } catch (error) {
      setMessages((items) => [
        ...items,
        {
          role: "assistant",
          content: "An error occurred while communicating with the assistant. Make sure the backend and local model runtime (Ollama) are active."
        }
      ]);
    }
  }

  return (
    <>
      <PageHeader title="Chat Assistant" subtitle="Ask grounded questions and review every source used in the answer." />
      <section className="flex h-[calc(100vh-150px)] flex-col rounded-md border border-line bg-white">
        <div className="flex-1 space-y-4 overflow-auto p-4">
          {messages.map((message, index) => (
            <div key={index} className={message.role === "user" ? "ml-auto max-w-2xl rounded-md bg-brand p-3 text-white" : "max-w-3xl rounded-md bg-slate-100 p-3"}>
              <p className="whitespace-pre-wrap text-sm leading-6">{message.content}</p>
              {message.sources?.length ? (
                <div className="mt-3 border-t border-line pt-2 text-xs text-slate-600">
                  Sources: {message.sources.map((source) => `${source.document_name}${source.page_number ? ` p.${source.page_number}` : ""}`).join(", ")}
                </div>
              ) : null}
            </div>
          ))}
        </div>
        <form onSubmit={submit} className="flex gap-2 border-t border-line p-3">
          <input className="h-11 flex-1 rounded-md border border-line px-3" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask about the knowledge base" />
          <button className="flex h-11 w-11 items-center justify-center rounded-md bg-brand text-white" title="Send">
            <Send size={18} />
          </button>
        </form>
      </section>
    </>
  );
}

