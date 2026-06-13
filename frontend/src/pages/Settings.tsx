import { useState } from "react";
import { KeyRound, Loader2, AlertCircle } from "lucide-react";
import { PageHeader } from "../components/PageHeader";

const rows = [
  ["LLM provider", "ollama"],
  ["Default model", "mistral"],
  ["Embedding model", "BAAI/bge-small-en-v1.5"],
  ["Vector store", "faiss"],
  ["Database", "sqlite"]
];

export function Settings({ token, role }: { token: string; role: string }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isPending, setIsPending] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const showSystemConfig = role === "admin" || role === "knowledge_manager";

  async function handlePasswordChange(e: React.FormEvent) {
    e.preventDefault();
    setErrorMsg("");
    setSuccessMsg("");

    if (!currentPassword.trim() || !newPassword.trim() || !confirmPassword.trim()) {
      setErrorMsg("All fields are required.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setErrorMsg("New passwords do not match.");
      return;
    }
    if (newPassword.length < 6) {
      setErrorMsg("Password must be at least 6 characters.");
      return;
    }

    setIsPending(true);
    try {
      const response = await fetch("/api/auth/change-password", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword
        })
      });

      if (!response.ok) {
        const txt = await response.text();
        throw new Error(txt);
      }

      setSuccessMsg("Password changed successfully!");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: any) {
      let msg = "Failed to update password.";
      try {
        const parsed = JSON.parse(err.message);
        if (parsed.detail) msg = parsed.detail;
      } catch {
        if (err.message) msg = err.message;
      }
      setErrorMsg(msg);
    } finally {
      setIsPending(false);
    }
  }

  return (
    <>
      <PageHeader title="Settings" subtitle="Manage your profile settings and view system variables." />
      
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-6 items-start">
        {/* Left column: System Configuration for Admins/Managers, or info for standard users */}
        <div>
          {showSystemConfig ? (
            <div className="rounded-md border border-line bg-white overflow-hidden">
              <div className="bg-slate-50 border-b border-line px-4 py-3">
                <h3 className="text-sm font-semibold text-slate-800">System Configuration</h3>
              </div>
              {rows.map(([label, value]) => (
                <div key={label} className="grid grid-cols-[240px_1fr] border-b border-line px-4 py-3 text-sm last:border-b-0">
                  <span className="font-medium text-slate-700">{label}</span>
                  <code className="text-slate-800 font-mono text-xs">{value}</code>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-md border border-line bg-white p-5 text-sm text-slate-600">
              <h3 className="font-semibold text-slate-800 mb-2">Internal RAG Assistant</h3>
              <p className="leading-6">
                Welcome to KnowledgeHub AI! You are logged in with the standard <strong>User</strong> role.
                This role allows you to chat with the assistant and search organization documents.
                To change your password, please use the form on the right. Contact your local administrator
                if you need access level changes or knowledge management privileges.
              </p>
            </div>
          )}
        </div>

        {/* Right column: Change Password Form */}
        <div className="rounded-md border border-line bg-white p-5">
          <h3 className="text-sm font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <KeyRound size={16} className="text-brand" />
            Change Password
          </h3>
          <form onSubmit={handlePasswordChange} className="space-y-4">
            {errorMsg && (
              <div className="rounded bg-red-50 p-2.5 text-xs text-red-700 border border-red-200 flex items-start gap-1.5">
                <AlertCircle size={14} className="shrink-0 mt-0.5" />
                <span>{errorMsg}</span>
              </div>
            )}
            {successMsg && (
              <div className="rounded bg-emerald-50 p-2.5 text-xs text-emerald-700 border border-emerald-200">
                {successMsg}
              </div>
            )}
            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1">Current Password</label>
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full h-9 px-3 rounded border border-line text-sm focus:border-brand focus:outline-none"
                placeholder="••••••••"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1">New Password</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full h-9 px-3 rounded border border-line text-sm focus:border-brand focus:outline-none"
                placeholder="••••••••"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1">Confirm New Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full h-9 px-3 rounded border border-line text-sm focus:border-brand focus:outline-none"
                placeholder="••••••••"
              />
            </div>
            <button
              type="submit"
              disabled={isPending}
              className="w-full h-9 bg-brand text-white font-medium text-sm rounded hover:bg-brand/90 transition flex items-center justify-center gap-1.5 disabled:opacity-60"
            >
              {isPending && <Loader2 size={14} className="animate-spin" />}
              Update Password
            </button>
          </form>
        </div>
      </div>
    </>
  );
}
