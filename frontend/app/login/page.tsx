'use client';

import { useAuth } from "@/shared/auth/AuthContext";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

   const { login } = useAuth();

const success = await login(email, password);

if (success) {
  router.push("/");
} else {
  setError("Invalid email or password");
}

    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-[#0a0f1c] flex items-center justify-center">
      <div className="bg-zinc-900 p-10 rounded-3xl w-full max-w-md border border-zinc-700">
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold text-sky-400">BHUDI RMM</h1>
          <p className="text-zinc-400 mt-2">Enterprise Access Control</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <input
            type="email"
            placeholder="admin@bhudi.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full bg-zinc-800 p-4 rounded-2xl focus:outline-none focus:ring-2 focus:ring-sky-500"
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full bg-zinc-800 p-4 rounded-2xl focus:outline-none focus:ring-2 focus:ring-sky-500"
            required
          />

          {error && <p className="text-red-500 text-center">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-sky-600 hover:bg-sky-500 py-4 rounded-2xl font-semibold transition disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <p className="text-center text-xs text-zinc-500 mt-8">
          Demo Account: admin@bhudi.com / admin123
        </p>
      </div>
    </div>
  );
}