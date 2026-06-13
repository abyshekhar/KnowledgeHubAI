import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { UserPlus, Loader2, AlertCircle, FolderPlus } from "lucide-react";
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

  const [resettingUser, setResettingUser] = useState<UserRow | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [resetError, setResetError] = useState("");
  const [resetSuccess, setResetSuccess] = useState(false);

  const [activeSubTab, setActiveSubTab] = useState<"users" | "categories">("users");
  const [newCatName, setNewCatName] = useState("");
  const [newCatDesc, setNewCatDesc] = useState("");
  const [catErrorMsg, setCatErrorMsg] = useState("");

  const categoriesQuery = useQuery({
    queryKey: ["categories"],
    queryFn: () => api<Array<{ id: number; name: string; description: string | null }>>("/categories", token)
  });

  const [editingCatId, setEditingCatId] = useState<number | null>(null);
  const [editingCatName, setEditingCatName] = useState("");
  const [editingCatDesc, setEditingCatDesc] = useState("");

  const updateCategoryMutation = useMutation({
    mutationFn: async ({ id, name, description }: { id: number; name: string; description: string | null }) => {
      const response = await fetch(`/api/categories/${id}`, {
        method: "PUT",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ name, description })
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      return response.json();
    },
    onSuccess: () => {
      setEditingCatId(null);
      categoriesQuery.refetch();
    },
    onError: (err: any) => {
      let msg = "Failed to update category.";
      try {
        const parsed = JSON.parse(err.message);
        if (parsed.detail) msg = parsed.detail;
      } catch {
        if (err.message) msg = err.message;
      }
      alert(msg);
    }
  });

  const startEditingCategory = (cat: { id: number; name: string; description: string | null }) => {
    setEditingCatId(cat.id);
    setEditingCatName(cat.name);
    setEditingCatDesc(cat.description || "");
  };

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

  const resetPasswordMutation = useMutation({
    mutationFn: async ({ id, newPassword }: { id: number; newPassword: string }) => {
      const response = await fetch(`/api/users/${id}`, {
        method: "PUT",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ password: newPassword })
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      return response.json();
    },
    onSuccess: () => {
      setResetSuccess(true);
      setNewPassword("");
      setTimeout(() => {
        setResettingUser(null);
        setResetSuccess(false);
      }, 1500);
    },
    onError: (err: any) => {
      setResetError(err.message || "Failed to reset password.");
    }
  });

  const handleResetPassword = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPassword.trim()) {
      setResetError("Password cannot be empty.");
      return;
    }
    if (newPassword.length < 6) {
      setResetError("Password must be at least 6 characters.");
      return;
    }
    setResetError("");
    resetPasswordMutation.mutate({ id: resettingUser!.id, newPassword });
  };

  const createCategoryMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch("/api/categories", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ name: newCatName, description: newCatDesc })
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      return response.json();
    },
    onSuccess: () => {
      setNewCatName("");
      setNewCatDesc("");
      setCatErrorMsg("");
      categoriesQuery.refetch();
    },
    onError: (err: any) => {
      setCatErrorMsg(err.message || "Failed to create category.");
    }
  });

  const deleteCategoryMutation = useMutation({
    mutationFn: async (id: number) => {
      const response = await fetch(`/api/categories/${id}`, {
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
    onSuccess: () => {
      categoriesQuery.refetch();
    }
  });

  const handleCreateCategory = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCatName.trim()) {
      setCatErrorMsg("Category Name is required.");
      return;
    }
    createCategoryMutation.mutate();
  };

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
      <PageHeader title="Admin Portal" subtitle="Administer organization users, system roles, categories, and parameters." />

      <div className="mb-6 flex gap-4 border-b border-line">
        <button
          onClick={() => setActiveSubTab("users")}
          className={`pb-2 text-sm font-semibold border-b-2 transition ${
            activeSubTab === "users" ? "border-brand text-brand" : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          User Accounts
        </button>
        <button
          onClick={() => setActiveSubTab("categories")}
          className={`pb-2 text-sm font-semibold border-b-2 transition ${
            activeSubTab === "categories" ? "border-brand text-brand" : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          Category Master
        </button>
      </div>

      {activeSubTab === "users" ? (
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
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => setResettingUser(u)}
                        className="text-xs font-semibold px-2.5 py-1 rounded transition text-slate-600 bg-slate-50 hover:bg-slate-100 border border-line"
                      >
                        Reset Password
                      </button>
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
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6 items-start animate-in fade-in duration-200">
          {/* Create Category Card */}
          <div className="rounded-md border border-line bg-white p-5">
            <h3 className="text-sm font-semibold text-slate-800 mb-4 flex items-center gap-2">
              <FolderPlus size={16} className="text-brand" />
              Add New Category
            </h3>
            <form onSubmit={handleCreateCategory} className="space-y-4">
              {catErrorMsg && (
                <div className="rounded bg-red-50 p-2 text-xs text-red-700 border border-red-200 flex items-start gap-1">
                  <AlertCircle size={14} className="shrink-0 mt-0.5" />
                  <span>{catErrorMsg}</span>
                </div>
              )}
              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1">Category Name</label>
                <input
                  type="text"
                  value={newCatName}
                  onChange={(e) => setNewCatName(e.target.value)}
                  className="w-full h-9 px-3 rounded border border-line text-sm focus:border-brand focus:outline-none"
                  placeholder="e.g. HR-Internal"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1">Description (Optional)</label>
                <textarea
                  value={newCatDesc}
                  onChange={(e) => setNewCatDesc(e.target.value)}
                  className="w-full h-20 px-3 py-1.5 rounded border border-line text-sm focus:border-brand focus:outline-none resize-none"
                  placeholder="e.g. Documents relating to HR policies and guides"
                />
              </div>
              <button
                type="submit"
                disabled={createCategoryMutation.isPending}
                className="w-full h-9 bg-brand text-white font-medium text-sm rounded hover:bg-brand/90 transition flex items-center justify-center gap-1.5 disabled:opacity-60"
              >
                {createCategoryMutation.isPending && <Loader2 size={14} className="animate-spin" />}
                Create Category
              </button>
            </form>
          </div>

          {/* Categories Table */}
          <div className="overflow-hidden rounded-md border border-line bg-white">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-4 py-3">Category Name</th>
                  <th className="px-4 py-3">Description</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {categoriesQuery.isLoading ? (
                  <tr>
                    <td colSpan={3} className="px-4 py-8 text-center text-slate-400">
                      <Loader2 className="animate-spin inline mr-2" size={16} />
                      Loading categories...
                    </td>
                  </tr>
                ) : (categoriesQuery.data ?? []).map((cat) => (
                  <tr key={cat.id} className="border-t border-line hover:bg-slate-50/40">
                    {editingCatId === cat.id ? (
                      <>
                        <td className="px-4 py-2">
                          <input
                            type="text"
                            value={editingCatName}
                            onChange={(e) => setEditingCatName(e.target.value)}
                            className="h-8 w-full px-2 rounded border border-line text-sm focus:border-brand focus:outline-none"
                          />
                        </td>
                        <td className="px-4 py-2">
                          <input
                            type="text"
                            value={editingCatDesc}
                            onChange={(e) => setEditingCatDesc(e.target.value)}
                            className="h-8 w-full px-2 rounded border border-line text-sm focus:border-brand focus:outline-none"
                          />
                        </td>
                        <td className="px-4 py-2 text-right">
                          <div className="flex justify-end gap-2">
                            <button
                              onClick={() => updateCategoryMutation.mutate({ id: cat.id, name: editingCatName, description: editingCatDesc || null })}
                              className="text-xs font-semibold px-2.5 py-1 rounded transition text-white bg-brand hover:bg-brand/90"
                            >
                              Save
                            </button>
                            <button
                              onClick={() => setEditingCatId(null)}
                              className="text-xs font-semibold px-2.5 py-1 rounded transition text-slate-600 bg-slate-50 border border-line hover:bg-slate-100"
                            >
                              Cancel
                            </button>
                          </div>
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="px-4 py-3 font-medium text-slate-700">{cat.name}</td>
                        <td className="px-4 py-3 text-slate-600">{cat.description || "-"}</td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex justify-end gap-2">
                            <button
                              onClick={() => startEditingCategory(cat)}
                              className="text-xs font-semibold px-2.5 py-1 rounded transition text-slate-600 bg-slate-50 hover:bg-slate-100 border border-line"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => {
                                if (confirm(`Are you sure you want to delete category "${cat.name}"?`)) {
                                  deleteCategoryMutation.mutate(cat.id);
                                }
                              }}
                              className="text-xs font-semibold px-2.5 py-1 rounded transition text-red-600 bg-red-50 hover:bg-red-100 border border-red-200"
                              title="Delete category"
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {resettingUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-lg border border-line bg-white p-6 shadow-xl animate-in fade-in zoom-in-95 duration-150">
            <h3 className="text-base font-semibold text-slate-900 mb-2">
              Reset Password
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Enter a new password for <span className="font-semibold">{resettingUser.full_name}</span> ({resettingUser.email}).
            </p>
            
            <form onSubmit={handleResetPassword} className="space-y-4">
              {resetError && (
                <div className="rounded bg-red-50 p-2.5 text-xs text-red-700 border border-red-200 flex items-start gap-1.5">
                  <AlertCircle size={14} className="shrink-0 mt-0.5" />
                  <span>{resetError}</span>
                </div>
              )}
              {resetSuccess && (
                <div className="rounded bg-emerald-50 p-2.5 text-xs text-emerald-700 border border-emerald-200">
                  Password updated successfully!
                </div>
              )}
              
              <div>
                <label className="block text-xs font-semibold text-slate-500 mb-1">New Password</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full h-9 px-3 rounded border border-line text-sm focus:border-brand focus:outline-none"
                  placeholder="Minimum 6 characters"
                  disabled={resetSuccess}
                  autoFocus
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setResettingUser(null);
                    setNewPassword("");
                    setResetError("");
                    setResetSuccess(false);
                  }}
                  className="h-9 px-4 rounded border border-line text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  {resetSuccess ? "Close" : "Cancel"}
                </button>
                {!resetSuccess && (
                  <button
                    type="submit"
                    disabled={resetPasswordMutation.isPending}
                    className="h-9 px-4 rounded bg-brand text-white text-sm font-medium hover:bg-brand/90 disabled:opacity-60 flex items-center gap-1.5"
                  >
                    {resetPasswordMutation.isPending && <Loader2 size={14} className="animate-spin" />}
                    Save Password
                  </button>
                )}
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
