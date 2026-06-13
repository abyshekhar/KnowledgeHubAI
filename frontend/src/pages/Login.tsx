import { LockKeyhole } from "lucide-react";
import { FormEvent, useState } from "react";

export function Login({ onAuthenticated }: { onAuthenticated: (token: string) => void }) {
  const [email, setEmail] = useState("admin@knowledgehub.local");
  const [password, setPassword] = useState("ChangeMe123!");
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    if (!response.ok) {
      setError("Sign-in failed");
      return;
    }
    const data = await response.json();
    onAuthenticated(data.access_token);
  }

  return (
    <main className="grid min-h-screen grid-cols-[1.1fr_0.9fr] bg-panel text-ink">
      <section className="flex flex-col justify-center px-16">
        <div className="max-w-2xl">
          <h1 className="text-5xl font-semibold tracking-normal">KnowledgeHub AI</h1>
          <p className="mt-5 max-w-xl text-lg leading-8 text-slate-600">
            Private, offline retrieval-augmented knowledge search for policies, procedures, training material, and internal documentation.
          </p>
          <div className="mt-8 grid grid-cols-3 gap-3 text-sm">
            {["Offline first", "Local models", "Source citations"].map((item) => (
              <div key={item} className="rounded-md border border-line bg-white px-4 py-3 font-medium">
                {item}
              </div>
            ))}
          </div>
        </div>
      </section>
      <section className="flex items-center justify-center bg-white px-10">
        <form onSubmit={submit} className="w-full max-w-sm rounded-md border border-line p-6">
          <div className="mb-5 flex h-10 w-10 items-center justify-center rounded-md bg-brand text-white">
            <LockKeyhole size={20} />
          </div>
          <h2 className="text-xl font-semibold">Sign in</h2>
          <label className="mt-5 block text-sm font-medium">Email</label>
          <input className="mt-2 h-10 w-full rounded-md border border-line px-3" value={email} onChange={(event) => setEmail(event.target.value)} />
          <label className="mt-4 block text-sm font-medium">Password</label>
          <input className="mt-2 h-10 w-full rounded-md border border-line px-3" type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          {error && <p className="mt-3 text-sm text-red-700">{error}</p>}
          <button className="mt-5 h-10 w-full rounded-md bg-brand font-medium text-white">Sign in</button>
        </form>
      </section>
    </main>
  );
}

