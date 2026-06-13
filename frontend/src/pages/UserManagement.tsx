import { PageHeader } from "../components/PageHeader";

export function UserManagement({ token }: { token: string }) {
  void token;
  return (
    <>
      <PageHeader title="User Management" subtitle="Administer users, roles, access, and audit posture." />
      <div className="rounded-md border border-line bg-white p-4">
        <div className="grid grid-cols-[1fr_180px_140px] border-b border-line pb-3 text-sm font-medium text-slate-600">
          <span>User</span>
          <span>Role</span>
          <span>Status</span>
        </div>
        <div className="grid grid-cols-[1fr_180px_140px] py-3 text-sm">
          <span>admin@knowledgehub.local</span>
          <span>Admin</span>
          <span>Active</span>
        </div>
      </div>
    </>
  );
}

