import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { UserPlus, Loader2, AlertCircle } from "lucide-react";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";

type UserRow = {
  id: number;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
};

export function UserManagement({ token }: { token: string }) {
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("user");
  const [errorMsg, setErrorMsg] = useState("");

  const usersQuery = useQuery({
    queryKey: ["users"],
    queryFn: () => api<UserRow[]>("/users", token)
  });

  const createUserMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch("/api/users", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ email, full_name: fullName, password, role })
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      return response.json();
    },
    onSuccess: () => {
      setEmail("");
      setFullName("");
      setPassword("");
      setRole("user");
      setErrorMsg("");
      usersQuery.refetch();
    },
    onError: (err: any) => {
      setErrorMsg(err.message || "Failed to create user.");
    }
  });

  const updateRoleMutation = useMutation({
    mutationFn: async ({ id, newRole }: { id: number; newRole: string }) => {
      const response = await fetch(`/api/users/${id}`, {
        method: "PUT",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ role: newRole })
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      return response.json();
    },
    onSuccess: () => {
      usersQuery.refetch();
    }
  });

  const toggleStatusMutation = useMutation({
    mutationFn: async ({ id, isActive }: { id: number; isActive: boolean }) => {
      const response = await fetch(`/api/users/${id}`, {
        method: "PUT",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ is_active: !isActive })
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      return response.json();
    },
    onSuccess: () => {
      usersQuery.refetch();
    }
  });

  const handleCreateUser = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !fullName.trim() || !password.trim()) {
      setErrorMsg("All fields are required.");
      return;
    }
    createUserMutation.mutate();
  };

  return (
    <>
      <PageHeader title="User Management" subtitle="Administer organization users, system roles, and account access." />

      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6 items-start">
        {/* Create User Card */}
        <div className="rounded-md border border-line bg-white p-5">
          <h3 className="text-sm font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <UserPlus size={16} className="text-brand" />
            Add New User
          </h3>
          <form onSubmit={handleCreateUser} className="space-y-4">
            {errorMsg && (
              <div className="rounded bg-red-50 p-2 text-xs text-red-700 border border-red-200 flex items-start gap-1">
                <AlertCircle size={14} className="shrink-0 mt-0.5" />
                <span>{errorMsg}</span>
              </div>
            )}
            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1">Full Name</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full h-9 px-3 rounded border border-line text-sm"
                placeholder="John Doe"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1">Email Address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full h-9 px-3 rounded border border-line text-sm"
                placeholder="john@organization.com"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full h-9 px-3 rounded border border-line text-sm"
                placeholder="••••••••"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1">System Role</label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full h-9 px-2 rounded border border-line bg-white text-sm"
              >
                <option value="user">Standard User</option>
                <option value="knowledge_manager">Knowledge Manager</option>
                <option value="admin">Administrator</option>
              </select>
            </div>
            <button
              type="submit"
              disabled={createUserMutation.isPending}
              className="w-full h-9 bg-brand text-white font-medium text-sm rounded hover:bg-brand/90 transition flex items-center justify-center gap-1.5 disabled:opacity-60"
            >
              {createUserMutation.isPending && <Loader2 size={14} className="animate-spin" />}
              Create Account
            </button>
          </form>
        </div>

        {/* Users Table */}
        <div className="overflow-hidden rounded-md border border-line bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="px-4 py-3">Full Name</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {usersQuery.isLoading ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-slate-400">
                    <Loader2 className="animate-spin inline mr-2" size={16} />
                    Loading accounts...
                  </td>
                </tr>
              ) : (usersQuery.data ?? []).map((u) => (
                <tr key={u.id} className="border-t border-line hover:bg-slate-50/40">
                  <td className="px-4 py-3 font-medium text-slate-700">{u.full_name}</td>
                  <td className="px-4 py-3 text-slate-600">{u.email}</td>
                  <td className="px-4 py-3">
                    <select
                      value={u.role}
                      onChange={(e) => updateRoleMutation.mutate({ id: u.id, newRole: e.target.value })}
                      disabled={u.email === "admin@knowledgehub.local"}
                      className="h-8 px-1 rounded border border-line bg-white text-xs text-slate-700 disabled:opacity-65"
                    >
                      <option value="user">Standard User</option>
                      <option value="knowledge_manager">Knowledge Manager</option>
                      <option value="admin">Administrator</option>
                    </select>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${
                        u.is_active
                          ? "bg-emerald-50 text-emerald-700 ring-emerald-600/10"
                          : "bg-red-50 text-red-700 ring-red-600/10"
                      }`}
                    >
                      {u.is_active ? "Active" : "Disabled"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => toggleStatusMutation.mutate({ id: u.id, isActive: u.is_active })}
                      disabled={u.email === "admin@knowledgehub.local"}
                      className={`text-xs font-semibold px-2.5 py-1 rounded transition disabled:opacity-40 ${
                        u.is_active
                          ? "text-red-600 bg-red-50 hover:bg-red-100"
                          : "text-emerald-600 bg-emerald-50 hover:bg-emerald-100"
                      }`}
                    >
                      {u.is_active ? "Deactivate" : "Activate"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
