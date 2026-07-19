import { Bot, ClipboardList, FileText, HelpCircle, LayoutDashboard, LogOut, Settings, Users } from "lucide-react";
import type { ReactNode } from "react";

const items = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "knowledge", label: "Knowledge Base", icon: FileText },
  { id: "chat", label: "Chat Assistant", icon: Bot },
  { id: "testgen", label: "Test Generator", icon: ClipboardList },
  { id: "users", label: "Users", icon: Users },
  { id: "settings", label: "Settings", icon: Settings },
  { id: "help", label: "Help Guide", icon: HelpCircle }
];

export function AppLayout({
  activePage,
  onNavigate,
  onLogout,
  role = "user",
  children
}: {
  activePage: string;
  onNavigate: (page: string) => void;
  onLogout: () => void;
  role?: string;
  children: ReactNode;
}) {
  const filteredItems = items.filter((item) => {
    const roleLower = role.toLowerCase();
    if (roleLower === "admin") return true;
    if (roleLower === "knowledge_manager") {
      return item.id !== "users";
    }
    return (
      item.id === "dashboard" || item.id === "chat" || item.id === "testgen" ||
      item.id === "settings" || item.id === "help"
    );
  });

  return (
    <div className="min-h-screen bg-panel text-ink">
      <aside className="fixed inset-y-0 left-0 w-64 border-r border-line bg-white">
        <div className="border-b border-line px-5 py-4">
          <h1 className="text-lg font-semibold">KnowledgeHub AI</h1>
          <p className="text-xs text-slate-500">Offline knowledge assistant</p>
        </div>
        <nav className="space-y-1 p-3">
          {filteredItems.map((item) => {
            const Icon = item.icon;
            const active = item.id === activePage;
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={`flex h-10 w-full items-center gap-3 rounded-md px-3 text-left text-sm ${
                  active ? "bg-brand text-white" : "text-slate-700 hover:bg-slate-100"
                }`}
              >
                <Icon size={17} />
                {item.label}
              </button>
            );
          })}
        </nav>
        <button
          onClick={onLogout}
          className="absolute bottom-4 left-3 right-3 flex h-10 items-center gap-3 rounded-md px-3 text-sm text-slate-700 hover:bg-slate-100"
        >
          <LogOut size={17} />
          Sign out
        </button>
      </aside>
      <main className="ml-64 min-h-screen p-6">{children}</main>
    </div>
  );
}

