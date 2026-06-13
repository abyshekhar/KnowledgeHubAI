import React, { useMemo, useState } from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppLayout } from "./layouts/AppLayout";
import { Dashboard } from "./pages/Dashboard";
import { KnowledgeBase } from "./pages/KnowledgeBase";
import { ChatAssistant } from "./pages/ChatAssistant";
import { UserManagement } from "./pages/UserManagement";
import { Settings } from "./pages/Settings";
import { Login } from "./pages/Login";
import "./styles/index.css";

const client = new QueryClient();

function App() {
  const [token, setToken] = useState(localStorage.getItem("knowledgehub_token") ?? "");
  const [page, setPage] = useState(localStorage.getItem("knowledgehub_page") ?? "dashboard");
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

  if (!token) {
    return <Login onAuthenticated={auth.setToken} />;
  }

  const pages: Record<string, React.ReactNode> = {
    dashboard: <Dashboard token={token} />,
    knowledge: <KnowledgeBase token={token} />,
    chat: <ChatAssistant token={token} />,
    users: <UserManagement token={token} />,
    settings: <Settings />
  };

  const handleNavigate = (nextPage: string) => {
    localStorage.setItem("knowledgehub_page", nextPage);
    setPage(nextPage);
  };

  const handleLogout = () => {
    localStorage.removeItem("knowledgehub_page");
    auth.setToken("");
  };

  return (
    <AppLayout activePage={page} onNavigate={handleNavigate} onLogout={handleLogout}>
      {pages[page]}
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

