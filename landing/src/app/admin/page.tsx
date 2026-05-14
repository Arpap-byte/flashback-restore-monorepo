"use client";

import { useState, useEffect } from "react";
import { X, Users, Wrench, HardDrive, Coins, Search, RefreshCw, Filter } from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────

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

interface UtilisateurDetail {
  id: string;
  email: string;
  plan: string;
  credits: number;
  credits_utilises: number;
  derniere_activite: string | null;
  cree_le: string | null;
  essais_restants: number;
}

interface TravailDetail {
  id: string;
  type: string;
  statut: string;
  cree_le: string | null;
  taille_original: number | null;
  taille_resultat: number | null;
  message_erreur: string | null;
  email_utilisateur: string | null;
}

type ModalType = "utilisateurs" | "actifs" | "plans" | "travaux" | "travaux_type" | "travaux_statut" | "credits" | "user_detail" | null;

// ── Helpers ─────────────────────────────────────────────────────────

const STORAGE_KEY = "flashback_admin_key";
const API_BASE = "";

function formatMo(mb: number): string {
  if (mb < 1) return "< 1 Mo";
  if (mb < 1024) return `${mb.toFixed(1)} Mo`;
  return `${(mb / 1024).toFixed(1)} Go`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

const PLAN_BADGE: Record<string, string> = {
  gratuit: "bg-zinc-700 text-zinc-300",
  decouverte: "bg-orange-500/20 text-orange-400",
  premium: "bg-amber-500/20 text-amber-400",
  annuel: "bg-violet-500/20 text-violet-400",
  pro: "bg-blue-500/20 text-blue-400",
};

const STATUT_BADGE: Record<string, string> = {
  termine: "bg-emerald-500/20 text-emerald-400",
  en_cours: "bg-amber-500/20 text-amber-400",
  erreur: "bg-red-500/20 text-red-400",
  cree: "bg-zinc-600 text-zinc-400",
};

// ── Components ──────────────────────────────────────────────────────

function StatCard({
  label, value, sub, icon: Icon, onClick, accent = "amber",
}: {
  label: string; value: string | number; sub?: string;
  icon: React.ComponentType<{ className?: string }>;
  onClick?: () => void; accent?: "amber" | "emerald" | "violet" | "blue" | "red";
}) {
  const accentClasses: Record<string, string> = {
    amber: "hover:border-amber-500/40 hover:bg-amber-500/5",
    emerald: "hover:border-emerald-500/40 hover:bg-emerald-500/5",
    violet: "hover:border-violet-500/40 hover:bg-violet-500/5",
    blue: "hover:border-blue-500/40 hover:bg-blue-500/5",
    red: "hover:border-red-500/40 hover:bg-red-500/5",
  };

  return (
    <div
      onClick={onClick}
      className={`bg-white/5 border border-white/10 rounded-xl p-4 transition-all ${
        onClick ? "cursor-pointer " + accentClasses[accent] : ""
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="text-2xl font-bold text-white">{value}</div>
        <Icon className="w-5 h-5 text-zinc-500" />
      </div>
      <div className="text-sm text-zinc-400">{label}</div>
      {sub && <div className="text-xs text-zinc-500 mt-1">{sub}</div>}
    </div>
  );
}

function Modal({
  title, onClose, children,
}: {
  title: string; onClose: () => void; children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div
        className="bg-zinc-900 border border-zinc-700 rounded-2xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-5 border-b border-zinc-800">
          <h2 className="text-lg font-semibold text-white">{title}</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white transition">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="flex-1 overflow-auto p-5">{children}</div>
      </div>
    </div>
  );
}

// ── Detail views ────────────────────────────────────────────────────

function UtilisateursList({ adminKey, onUserClick }: { adminKey: string; onUserClick?: (userId: string) => void }) {
  const [users, setUsers] = useState<UtilisateurDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    fetch(`/api/admin/utilisateurs`, { headers: { "X-Admin-Key": adminKey } })
      .then((r) => r.json())
      .then((d) => { setUsers(d.utilisateurs); setLoading(false); })
      .catch(() => setLoading(false));
  }, [adminKey]);

  const filtered = filter
    ? users.filter((u) => u.email.toLowerCase().includes(filter.toLowerCase()) || u.plan.includes(filter))
    : users;

  if (loading) return <div className="text-zinc-400 text-center py-8 animate-pulse">Chargement...</div>;

  return (
    <div>
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
        <input
          type="text" placeholder="Filtrer par email ou plan..." value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="w-full bg-zinc-800 border border-zinc-700 rounded-lg pl-10 pr-4 py-2.5 text-white text-sm placeholder-zinc-500 focus:outline-none focus:border-amber-500"
        />
      </div>
      <div className="text-xs text-zinc-500 mb-3">{filtered.length} utilisateur(s)</div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-zinc-500 border-b border-zinc-800">
              <th className="text-left py-2 pr-4 font-medium">Email</th>
              <th className="text-left py-2 pr-4 font-medium">Plan</th>
              <th className="text-right py-2 pr-4 font-medium">Crédits</th>
              <th className="text-right py-2 pr-4 font-medium">Utilisés</th>
              <th className="text-right py-2 pr-4 font-medium">Essais</th>
              <th className="text-right py-2 font-medium">Activité</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((u) => (
              <tr key={u.id}
                className="border-b border-zinc-800/50 hover:bg-white/5 transition cursor-pointer"
                onClick={() => onUserClick?.(u.id)}
              >
                <td className="py-2.5 pr-4 text-zinc-300 truncate max-w-[180px]">{u.email}</td>
                <td className="py-2.5 pr-4">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PLAN_BADGE[u.plan] || "bg-zinc-700 text-zinc-300"}`}>
                    {u.plan}
                  </span>
                </td>
                <td className="py-2.5 pr-4 text-right text-zinc-300">{u.credits}</td>
                <td className="py-2.5 pr-4 text-right text-zinc-400">{u.credits_utilises}</td>
                <td className="py-2.5 pr-4 text-right text-zinc-400">{u.essais_restants}</td>
                <td className="py-2.5 text-right text-zinc-500 text-xs">{formatDate(u.derniere_activite)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TravauxList({ adminKey, type, statut }: { adminKey: string; type?: string; statut?: string }) {
  const [travaux, setTravaux] = useState<TravailDetail[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const params = new URLSearchParams();
    if (type) params.set("type", type);
    if (statut) params.set("statut", statut);
    fetch(`/api/admin/travaux?${params.toString()}`, { headers: { "X-Admin-Key": adminKey } })
      .then((r) => r.json())
      .then((d) => { setTravaux(d.travaux); setLoading(false); })
      .catch(() => setLoading(false));
  }, [adminKey, type, statut]);

  const titleParts = [];
  if (type) titleParts.push(type);
  if (statut) titleParts.push(statut);

  if (loading) return <div className="text-zinc-400 text-center py-8 animate-pulse">Chargement...</div>;

  return (
    <div>
      <div className="text-xs text-zinc-500 mb-3">{travaux.length} travail/travaux {titleParts.length ? `· ${titleParts.join(" · ")}` : ""}</div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-zinc-500 border-b border-zinc-800">
              <th className="text-left py-2 pr-3 font-medium">Type</th>
              <th className="text-left py-2 pr-3 font-medium">Statut</th>
              <th className="text-left py-2 pr-3 font-medium">Utilisateur</th>
              <th className="text-right py-2 pr-3 font-medium">Taille</th>
              <th className="text-right py-2 font-medium">Date</th>
            </tr>
          </thead>
          <tbody>
            {travaux.map((t) => (
              <tr key={t.id} className="border-b border-zinc-800/50 hover:bg-white/5 transition">
                <td className="py-2 pr-3 text-zinc-300 capitalize">{t.type}</td>
                <td className="py-2 pr-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUT_BADGE[t.statut] || "bg-zinc-600 text-zinc-400"}`}>
                    {t.statut}
                  </span>
                </td>
                <td className="py-2 pr-3 text-zinc-400 text-xs truncate max-w-[160px]">{t.email_utilisateur || "—"}</td>
                <td className="py-2 pr-3 text-right text-zinc-500 text-xs">
                  {t.taille_original ? formatMo(t.taille_original / (1024 * 1024)) : "—"}
                </td>
                <td className="py-2 text-right text-zinc-500 text-xs whitespace-nowrap">{formatDate(t.cree_le)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── User Detail View ────────────────────────────────────────────────

interface UserDetailResponse {
  utilisateur: {
    id: string;
    email: string;
    plan: string;
    credits: number;
    credits_consommes: number;
    derniere_activite: string | null;
    cree_le: string | null;
    essais_restants: number;
  };
  stockage: {
    original_mb: number;
    resultat_mb: number;
    total_mb: number;
    nb_photos: number;
    nb_videos: number;
    total_travaux_termines: number;
  };
  travaux_par_type: Array<{ type: string; statut: string; nb: number }>;
  derniers_travaux: Array<{
    id: string;
    type: string;
    statut: string;
    cree_le: string | null;
    taille_original: number | null;
    taille_resultat: number | null;
    message_erreur: string | null;
  }>;
}

function UserDetailView({ adminKey, userId }: { adminKey: string; userId: string }) {
  const [detail, setDetail] = useState<UserDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/admin/utilisateurs/${userId}`, { headers: { "X-Admin-Key": adminKey } })
      .then((r) => r.json())
      .then((d) => { setDetail(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [adminKey, userId]);

  if (loading) return <div className="text-zinc-400 text-center py-8 animate-pulse">Chargement...</div>;
  if (!detail) return <div className="text-red-400 text-center py-8">Erreur de chargement.</div>;

  const u = detail.utilisateur;
  const s = detail.stockage;

  return (
    <div className="space-y-6">
      {/* Infos utilisateur */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-white/5 border border-white/10 rounded-xl p-3">
          <div className="text-xs text-zinc-500">Email</div>
          <div className="text-white text-sm font-medium mt-0.5 truncate">{u.email}</div>
        </div>
        <div className="bg-white/5 border border-white/10 rounded-xl p-3">
          <div className="text-xs text-zinc-500">Plan</div>
          <div className="mt-1">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PLAN_BADGE[u.plan] || "bg-zinc-700 text-zinc-300"}`}>
              {u.plan}
            </span>
          </div>
        </div>
        <div className="bg-white/5 border border-white/10 rounded-xl p-3">
          <div className="text-xs text-zinc-500">Credits</div>
          <div className="text-white font-semibold mt-0.5">{u.credits} <span className="text-xs text-zinc-500 font-normal">disponibles</span></div>
          <div className="text-xs text-zinc-500">{u.credits_consommes} consommes</div>
        </div>
        <div className="bg-white/5 border border-white/10 rounded-xl p-3">
          <div className="text-xs text-zinc-500">Inscription</div>
          <div className="text-white text-sm mt-0.5">{formatDate(u.cree_le)}</div>
        </div>
      </div>

      {/* Stockage */}
      <div>
        <h3 className="text-sm font-semibold text-zinc-300 mb-3">Stockage utilise</h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-3 text-center">
            <div className="text-xl font-bold text-emerald-400">{s.nb_photos}</div>
            <div className="text-xs text-zinc-500">Photos</div>
          </div>
          <div className="bg-violet-500/5 border border-violet-500/20 rounded-xl p-3 text-center">
            <div className="text-xl font-bold text-violet-400">{s.nb_videos}</div>
            <div className="text-xs text-zinc-500">Videos</div>
          </div>
          <div className="bg-white/5 border border-white/10 rounded-xl p-3 text-center">
            <div className="text-xl font-bold text-white">{formatMo(s.original_mb)}</div>
            <div className="text-xs text-zinc-500">Originaux</div>
          </div>
          <div className="bg-white/5 border border-white/10 rounded-xl p-3 text-center">
            <div className="text-xl font-bold text-white">{formatMo(s.resultat_mb)}</div>
            <div className="text-xs text-zinc-500">Resultats</div>
          </div>
          <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-3 text-center">
            <div className="text-xl font-bold text-amber-400">{formatMo(s.total_mb)}</div>
            <div className="text-xs text-zinc-500">Total</div>
          </div>
        </div>
      </div>

      {/* Derniers travaux */}
      <div>
        <h3 className="text-sm font-semibold text-zinc-300 mb-3">Derniers travaux ({detail.derniers_travaux.length})</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-zinc-500 border-b border-zinc-800">
                <th className="text-left py-2 pr-3 font-medium">Type</th>
                <th className="text-left py-2 pr-3 font-medium">Statut</th>
                <th className="text-right py-2 pr-3 font-medium">Taille</th>
                <th className="text-right py-2 font-medium">Date</th>
              </tr>
            </thead>
            <tbody>
              {detail.derniers_travaux.map((t) => (
                <tr key={t.id} className="border-b border-zinc-800/50">
                  <td className="py-2 pr-3 text-zinc-300 capitalize">{t.type}</td>
                  <td className="py-2 pr-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUT_BADGE[t.statut] || "bg-zinc-600 text-zinc-400"}`}>
                      {t.statut}
                    </span>
                  </td>
                  <td className="py-2 pr-3 text-right text-zinc-500 text-xs">
                    {t.taille_resultat ? formatMo(t.taille_resultat / (1024 * 1024)) : "—"}
                  </td>
                  <td className="py-2 text-right text-zinc-500 text-xs whitespace-nowrap">{formatDate(t.cree_le)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function CreditsDetail({ data }: { data: DashboardData["credits"] }) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="bg-white/5 border border-white/10 rounded-xl p-4 text-center">
        <div className="text-3xl font-bold text-white">{data.total_distribues}</div>
        <div className="text-sm text-zinc-400 mt-1">Crédits distribués</div>
        <div className="text-xs text-zinc-500 mt-1">Total depuis le début</div>
      </div>
      <div className="bg-white/5 border border-white/10 rounded-xl p-4 text-center">
        <div className="text-3xl font-bold text-red-400">{data.total_consommes}</div>
        <div className="text-sm text-zinc-400 mt-1">Crédits consommés</div>
        <div className="text-xs text-zinc-500 mt-1">Total depuis le début</div>
      </div>
      <div className="col-span-2 bg-white/5 border border-white/10 rounded-xl p-4 text-center">
        <div className="text-3xl font-bold text-emerald-400">{data.credits_actifs}</div>
        <div className="text-sm text-zinc-400 mt-1">Crédits actifs en circulation</div>
        <div className="text-xs text-zinc-500 mt-1">{data.total_distribues - data.total_consommes} encore disponibles</div>
      </div>
    </div>
  );
}

// ── Page principale ─────────────────────────────────────────────────

// ── Section Logs de connexion ──────────────────────────────────────

interface AuditLogEntry {
  id: string;
  evenement: string;
  email: string | null;
  ip: string | null;
  reussite: number;
  detail: string | null;
  cree_le: string;
}

function AuditLogsSection({ adminKey }: { adminKey: string }) {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/audit-logs?limite=10", { headers: { "X-Admin-Key": adminKey } })
      .then((r) => r.json())
      .then((d) => { setLogs(d.logs || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, [adminKey]);

  if (loading) return <div className="text-zinc-500 text-sm animate-pulse">Chargement...</div>;
  if (logs.length === 0) return <div className="text-zinc-500 text-sm">Aucune connexion enregistrée.</div>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-zinc-500 border-b border-zinc-800">
            <th className="text-left py-2 pr-3 font-medium">Événement</th>
            <th className="text-left py-2 pr-3 font-medium">Email</th>
            <th className="text-left py-2 pr-3 font-medium">IP</th>
            <th className="text-left py-2 pr-3 font-medium">Résultat</th>
            <th className="text-right py-2 font-medium">Date</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr key={log.id} className="border-b border-zinc-800/50">
              <td className="py-2 pr-3 text-zinc-300 capitalize">{log.evenement}</td>
              <td className="py-2 pr-3 text-zinc-300 max-w-[180px] truncate">{log.email || "—"}</td>
              <td className="py-2 pr-3 text-zinc-500 font-mono text-xs">{log.ip || "—"}</td>
              <td className="py-2 pr-3">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${log.reussite ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"}`}>
                  {log.reussite ? "✅ OK" : "❌ Échec"}
                </span>
              </td>
              <td className="py-2 text-right text-zinc-500 text-xs whitespace-nowrap">{formatDate(log.cree_le)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Page principale ─────────────────────────────────────────────────

export default function AdminDashboard() {
  const [adminKey, setAdminKey] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [modal, setModal] = useState<{
    type: ModalType;
    title: string;
    extra?: { type?: string; statut?: string; userId?: string };
  } | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) { setAdminKey(stored); fetchDashboard(stored); }
  }, []);

  async function fetchDashboard(key?: string) {
    const k = key || adminKey;
    if (!k) return;
    setLoading(true); setError("");
    try {
      const res = await fetch("/api/admin/dashboard", { headers: { "X-Admin-Key": k } });
      if (!res.ok) { if (res.status === 403) throw new Error("Clé admin invalide."); throw new Error(`Erreur ${res.status}`); }
      setData(await res.json());
      setAuthenticated(true);
      localStorage.setItem(STORAGE_KEY, k);
    } catch (e: any) {
      setError(e.message); setAuthenticated(false); localStorage.removeItem(STORAGE_KEY);
    } finally { setLoading(false); }
  }

  function handleSubmit(e: React.FormEvent) { e.preventDefault(); fetchDashboard(); }

  const openModal = (type: ModalType, title: string, extra?: { type?: string; statut?: string; userId?: string }) =>
    setModal({ type, title, extra });

  const openUserDetail = (userId: string) =>
    setModal({ type: "user_detail", title: "Détail utilisateur", extra: { userId } });

  // ── Login screen ────────────────────────────────────────────────
  if (!authenticated) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-4">
        <form onSubmit={handleSubmit} className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8 max-w-sm w-full">
          <h1 className="text-xl font-bold text-white mb-6">🔐 Admin Flashback</h1>
          <input type="password" value={adminKey} onChange={(e) => setAdminKey(e.target.value)}
            placeholder="Clé administrateur"
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-3 text-white placeholder-zinc-500 mb-4 focus:outline-none focus:border-amber-500" autoFocus />
          <button type="submit" disabled={loading || !adminKey}
            className="w-full bg-amber-500 hover:bg-amber-400 disabled:bg-zinc-700 text-black font-semibold rounded-lg py-3 transition">
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
          <div>
            <h1 className="text-2xl font-bold text-white">📊 Dashboard Admin</h1>
            <p className="text-sm text-zinc-500 mt-1">Cliquez sur les cartes pour voir les détails</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => fetchDashboard()} disabled={loading}
              className={`p-2 rounded-lg text-zinc-400 hover:text-white transition ${loading ? "animate-spin" : ""}`}>
              <RefreshCw className="w-5 h-5" />
            </button>
            <button onClick={() => { setAuthenticated(false); setData(null); localStorage.removeItem(STORAGE_KEY); }}
              className="text-sm text-zinc-400 hover:text-white transition">Déconnexion</button>
          </div>
        </div>

        {/* Section Utilisateurs */}
        <section className="mb-6">
          <h2 className="text-lg font-semibold text-zinc-300 mb-3">👥 Utilisateurs</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="Total" value={data.utilisateurs.total} icon={Users}
              onClick={() => openModal("utilisateurs", "Tous les utilisateurs")} />
            <StatCard label="Actifs 7j" value={data.utilisateurs.actifs_7j} icon={Users} accent="emerald"
              onClick={() => openModal("actifs", "Utilisateurs actifs (7 jours)")} />
            <StatCard label="Actifs 30j" value={data.utilisateurs.actifs_30j} icon={Users} accent="emerald"
              onClick={() => openModal("actifs", "Utilisateurs actifs (30 jours)")} />
            <StatCard label="Plans" value={Object.keys(data.utilisateurs.par_plan).length} icon={Filter} accent="violet"
              sub={Object.entries(data.utilisateurs.par_plan).map(([p, n]) => `${p}: ${n}`).join(" · ")}
              onClick={() => openModal("plans", "Répartition par plan", { type: undefined })} />
          </div>
        </section>

        {/* Section Travaux */}
        <section className="mb-6">
          <h2 className="text-lg font-semibold text-zinc-300 mb-3">🔧 Travaux</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="Total" value={data.travaux.total} icon={Wrench}
              onClick={() => openModal("travaux", "Tous les travaux")} />
            <StatCard label="Photos stockées" value={data.travaux.photos_stockees} icon={HardDrive} accent="emerald" />
            <StatCard label="Par type" value={Object.keys(data.travaux.par_type).length} icon={Filter} accent="violet"
              sub={Object.entries(data.travaux.par_type).map(([t, n]) => `${t}: ${n}`).join(" · ") || "—"}
              onClick={() => openModal("travaux_type", "Travaux par type")} />
            <StatCard label="Statuts" value={Object.keys(data.travaux.par_statut).length} icon={Filter} accent="blue"
              sub={Object.entries(data.travaux.par_statut).map(([s, n]) => `${s}: ${n}`).join(" · ") || "—"}
              onClick={() => openModal("travaux_statut", "Travaux par statut")} />
          </div>
        </section>

        {/* Section Stockage */}
        <section className="mb-6">
          <h2 className="text-lg font-semibold text-zinc-300 mb-3">💾 Stockage</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <StatCard label="Espace total" value={formatMo(data.stockage.espace_total_mb)} icon={HardDrive} accent="emerald" />
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
            <StatCard label="Distribués" value={data.credits.total_distribues} icon={Coins} accent="amber"
              onClick={() => openModal("credits", "Détail des crédits")} />
            <StatCard label="Consommés" value={data.credits.total_consommes} icon={Coins} accent="red"
              onClick={() => openModal("credits", "Détail des crédits")} />
            <StatCard label="Actifs" value={data.credits.credits_actifs} icon={Coins} accent="emerald"
              onClick={() => openModal("credits", "Détail des crédits")} />
          </div>
        </section>

        {/* Section Connexions */}
        <section className="mb-6">
          <h2 className="text-lg font-semibold text-zinc-300 mb-3">🔐 Connexions</h2>
          <AuditLogsSection adminKey={adminKey} />
        </section>

        {/* Modals */}
        {modal && (
          <Modal title={modal.title} onClose={() => setModal(null)}>
            {modal.type === "utilisateurs" && <UtilisateursList adminKey={adminKey} onUserClick={openUserDetail} />}
            {modal.type === "plans" && (
              <div className="space-y-3">
                {Object.entries(data.utilisateurs.par_plan).map(([plan, nb]) => (
                  <div key={plan} className="flex items-center justify-between p-3 bg-white/5 border border-white/10 rounded-lg">
                    <span className={`text-sm px-2.5 py-1 rounded-full font-medium ${PLAN_BADGE[plan] || "bg-zinc-700 text-zinc-300"}`}>
                      {plan}
                    </span>
                    <span className="text-white font-semibold">{nb} utilisateur{nb > 1 ? "s" : ""}</span>
                  </div>
                ))}
              </div>
            )}
            {modal.type === "travaux" && <TravauxList adminKey={adminKey} />}
            {modal.type === "travaux_type" && (
              <div className="space-y-3">
                {Object.entries(data.travaux.par_type).map(([type, nb]) => (
                  <div key={type} className="p-3 bg-white/5 border border-white/10 rounded-lg cursor-pointer hover:bg-white/10 transition"
                    onClick={() => setModal({ type: "travaux", title: `Travaux · ${type}`, extra: { type } })}>
                    <div className="flex items-center justify-between">
                      <span className="text-zinc-300 capitalize font-medium">{type}</span>
                      <span className="text-white font-semibold">{nb}</span>
                    </div>
                    <div className="text-xs text-zinc-500 mt-1">Cliquer pour voir le détail →</div>
                  </div>
                ))}
              </div>
            )}
            {modal.type === "travaux_statut" && (
              <div className="space-y-3">
                {Object.entries(data.travaux.par_statut).map(([statut, nb]) => (
                  <div key={statut} className="p-3 bg-white/5 border border-white/10 rounded-lg cursor-pointer hover:bg-white/10 transition"
                    onClick={() => setModal({ type: "travaux", title: `Travaux · ${statut}`, extra: { statut } })}>
                    <div className="flex items-center justify-between">
                      <span className={`text-sm px-2.5 py-0.5 rounded-full font-medium ${STATUT_BADGE[statut] || "bg-zinc-600 text-zinc-400"}`}>
                        {statut}
                      </span>
                      <span className="text-white font-semibold">{nb}</span>
                    </div>
                    <div className="text-xs text-zinc-500 mt-1">Cliquer pour voir le détail →</div>
                  </div>
                ))}
              </div>
            )}
            {modal.type === "credits" && <CreditsDetail data={data.credits} />}
            {modal.type === "user_detail" && modal.extra?.userId && (
              <UserDetailView adminKey={adminKey} userId={modal.extra.userId} />
            )}
            {/* Re-render TravauxList with filters when drilling from type/statut */}
            {modal.type === "travaux" && modal.extra && (
              <TravauxList adminKey={adminKey} type={modal.extra.type} statut={modal.extra.statut} />
            )}
            {modal.type === "travaux" && !modal.extra && <TravauxList adminKey={adminKey} />}
          </Modal>
        )}
      </div>
    </div>
  );
}
