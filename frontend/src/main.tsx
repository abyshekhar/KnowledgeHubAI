import React, { useMemo, useState } from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { AppLayout } from "./layouts/AppLayout";
import { Dashboard } from "./pages/Dashboard";
import { KnowledgeBase } from "./pages/KnowledgeBase";
import { ChatAssistant } from "./pages/ChatAssistant";
import { TestGenerator } from "./pages/TestGenerator";
import { HelpGuide } from "./pages/HelpGuide";
import { UserManagement } from "./pages/UserManagement";
import { Settings } from "./pages/Settings";
import { Login } from "./pages/Login";
import { api } from "./api/client";
import { Loader2 } from "lucide-react";
import "./styles/index.css";

const client = new QueryClient();

function App() {
  const [token, setToken] = useState(localStorage.getItem("knowledgehub_token") ?? "");
  const [page, setPage] = useState(localStorage.getItem("knowledgehub_page") ?? "dashboard");
  const [selectedModel, setSelectedModelState] = useState(localStorage.getItem("knowledgehub_model") ?? "");

  const setSelectedModel = (value: string) => {
    localStorage.setItem("knowledgehub_model", value);
    setSelectedModelState(value);
  };

  const auth = useMemo(
    () => ({
      token,
      setToken: (value: string) => {
        localStorage.setItem("knowledgehub_token", value);
        setToken(value);
      }
    }),
    [token]
  );

  const profileQuery = useQuery({
    queryKey: ["profile", token],
    queryFn: () => api<{ id: number; email: string; full_name: string; role: string }>("/auth/me", token),
    enabled: !!token,
    retry: false
  });

  if (!token) {
    return <Login onAuthenticated={auth.setToken} />;
  }

  if (profileQuery.isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-brand" />
          <span className="text-sm text-slate-500 font-medium animate-pulse">Loading profile...</span>
        </div>
      </div>
    );
  }

  const userRole = profileQuery.data?.role?.toLowerCase() || "user";

  const pages: Record<string, React.ReactNode> = {
    dashboard: <Dashboard token={token} selectedModel={selectedModel} onSelectModel={setSelectedModel} />,
    chat: <ChatAssistant token={token} selectedModel={selectedModel} onSelectModel={setSelectedModel} />,
    testgen: <TestGenerator token={token} />,
    settings: <Settings token={token} role={userRole} />,
    help: <HelpGuide token={token} />,
    ...(userRole === "admin" || userRole === "knowledge_manager" ? {
      knowledge: <KnowledgeBase token={token} />,
    } : {}),
    ...(userRole === "admin" ? {
      users: <UserManagement token={token} />
    } : {})
  };

  const handleNavigate = (nextPage: string) => {
    if (nextPage === "users" && userRole !== "admin") return;
    if (nextPage === "knowledge" && userRole !== "admin" && userRole !== "knowledge_manager") return;

    localStorage.setItem("knowledgehub_page", nextPage);
    setPage(nextPage);
  };

  const handleLogout = () => {
    localStorage.removeItem("knowledgehub_page");
    auth.setToken("");
  };

  const activePageNode = pages[page] || (
    <Dashboard token={token} selectedModel={selectedModel} onSelectModel={setSelectedModel} />
  );

  return (
    <AppLayout activePage={page} onNavigate={handleNavigate} onLogout={handleLogout} role={userRole}>
      {activePageNode}
    </AppLayout>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
);

