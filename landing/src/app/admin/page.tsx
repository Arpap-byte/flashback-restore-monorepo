"use client";

import { useState, useEffect } from "react";

interface DashboardData {
  utilisateurs: {
    total: number;
    actifs_7j: number;
    actifs_30j: number;
    par_plan: Record<string, number>;
  };
  travaux: {
    total: number;
    photos_stockees: number;
    par_type: Record<string, number>;
    par_statut: Record<string, number>;
  };
  stockage: {
    espace_total_mb: number;
    top5_utilisateurs: Array<{ email: string; espace_mb: number }>;
  };
  credits: {
    total_distribues: number;
    total_consommes: number;
    credits_actifs: number;
  };
}

const STORAGE_KEY = "flashback_admin_key";

function formatMo(mb: number): string {
  if (mb < 1) return "< 1 Mo";
  if (mb < 1024) return `${mb.toFixed(1)} Mo`;
  return `${(mb / 1024).toFixed(1)} Go`;
}

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-4">
      <div className="text-2xl font-bold text-white">{value}</div>
      <div className="text-sm text-zinc-400">{label}</div>
      {sub && <div className="text-xs text-zinc-500 mt-1">{sub}</div>}
    </div>
  );
}

export default function AdminDashboard() {
  const [adminKey, setAdminKey] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      setAdminKey(stored);
      fetchDashboard(stored);
    }
  }, []);

  async function fetchDashboard(key?: string) {
    const k = key || adminKey;
    if (!k) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/admin/dashboard", {
        headers: { "X-Admin-Key": k },
      });
      if (!res.ok) {
        if (res.status === 403) throw new Error("Clé admin invalide.");
        throw new Error(`Erreur ${res.status}`);
      }
      const json = await res.json();
      setData(json);
      setAuthenticated(true);
      localStorage.setItem(STORAGE_KEY, k);
    } catch (e: any) {
      setError(e.message);
      setAuthenticated(false);
      localStorage.removeItem(STORAGE_KEY);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    fetchDashboard();
  }

  if (!authenticated) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-4">
        <form onSubmit={handleSubmit} className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8 max-w-sm w-full">
          <h1 className="text-xl font-bold text-white mb-6">🔐 Admin Flashback</h1>
          <input
            type="password"
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
            placeholder="Clé administrateur"
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-3 text-white placeholder-zinc-500 mb-4 focus:outline-none focus:border-amber-500"
            autoFocus
          />
          <button
            type="submit"
            disabled={loading || !adminKey}
            className="w-full bg-amber-500 hover:bg-amber-400 disabled:bg-zinc-700 text-black font-semibold rounded-lg py-3 transition"
          >
            {loading ? "Connexion..." : "Accéder au dashboard"}
          </button>
          {error && <p className="text-red-400 text-sm mt-3 text-center">{error}</p>}
        </form>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="min-h-screen bg-zinc-950 p-4 md:p-8">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-2xl font-bold text-white">📊 Dashboard Admin</h1>
          <button
            onClick={() => {
              setAuthenticated(false);
              setData(null);
              localStorage.removeItem(STORAGE_KEY);
            }}
            className="text-sm text-zinc-400 hover:text-white transition"
          >
            Déconnexion
          </button>
        </div>

        {/* Section Utilisateurs */}
        <section className="mb-6">
          <h2 className="text-lg font-semibold text-zinc-300 mb-3">👥 Utilisateurs</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="Total" value={data.utilisateurs.total} />
            <StatCard label="Actifs 7j" value={data.utilisateurs.actifs_7j} />
            <StatCard label="Actifs 30j" value={data.utilisateurs.actifs_30j} />
            <StatCard
              label="Plans"
              value={Object.keys(data.utilisateurs.par_plan).length}
              sub={Object.entries(data.utilisateurs.par_plan)
                .map(([plan, nb]) => `${plan}: ${nb}`)
                .join(" · ")}
            />
          </div>
        </section>

        {/* Section Travaux */}
        <section className="mb-6">
          <h2 className="text-lg font-semibold text-zinc-300 mb-3">🔧 Travaux</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="Total" value={data.travaux.total} />
            <StatCard label="Photos stockées" value={data.travaux.photos_stockees} />
            <StatCard
              label="Par type"
              value={data.travaux.par_type["restauration"] ?? 0}
              sub={
                Object.entries(data.travaux.par_type)
                  .map(([t, nb]) => `${t}: ${nb}`)
                  .join(" · ") || "—"
              }
            />
            <StatCard
              label="Statuts"
              value={Object.keys(data.travaux.par_statut).length}
              sub={
                Object.entries(data.travaux.par_statut)
                  .map(([s, nb]) => `${s}: ${nb}`)
                  .join(" · ") || "—"
              }
            />
          </div>
        </section>

        {/* Section Stockage */}
        <section className="mb-6">
          <h2 className="text-lg font-semibold text-zinc-300 mb-3">💾 Stockage</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <StatCard
              label="Espace total"
              value={formatMo(data.stockage.espace_total_mb)}
            />
            <div className="bg-white/5 border border-white/10 rounded-xl p-4">
              <div className="text-sm text-zinc-400 mb-2">Top 5 utilisateurs</div>
              {data.stockage.top5_utilisateurs.length === 0 ? (
                <div className="text-zinc-500 text-sm">Aucune donnée</div>
              ) : (
                <ul className="space-y-1">
                  {data.stockage.top5_utilisateurs.map((u, i) => (
                    <li key={i} className="flex justify-between text-sm">
                      <span className="text-zinc-300 truncate max-w-[200px]">{u.email}</span>
                      <span className="text-zinc-500 ml-2">{formatMo(u.espace_mb)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </section>

        {/* Section Crédits */}
        <section className="mb-6">
          <h2 className="text-lg font-semibold text-zinc-300 mb-3">💰 Crédits</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <StatCard label="Distribués" value={data.credits.total_distribues} />
            <StatCard label="Consommés" value={data.credits.total_consommes} />
            <StatCard label="Actifs" value={data.credits.credits_actifs} />
          </div>
        </section>
      </div>
    </div>
  );
}
