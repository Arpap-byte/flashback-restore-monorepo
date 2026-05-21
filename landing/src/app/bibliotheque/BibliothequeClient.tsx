"use client";

import { useState, useEffect, useMemo, useCallback, Suspense } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  Upload,
  Images,
  Sparkles,
  Film,
  AlertTriangle,
  Loader2,
  History,
  ArrowRight,
} from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { useUser, useAuth as useClerkAuth } from "@clerk/nextjs";
import {
  uploadToLibrary,
  listLibrary,
  deleteLibraryImage,
  getPhotoUrl,
  LibraryImage,
  getUserHistory,
  deleteTravail,
  deleteAllHistory,
  updatePreferences,
  TravailHistorique,
  UserHistoryResponse,
} from "@/lib/api";

import ImporteesTab, { type ImporteeItem } from "./tabs/ImporteesTab";
import RetoucheesTab from "./tabs/RetoucheesTab";
import AnimationsTab from "./tabs/AnimationsTab";
import RetentionBar from "./tabs/RetentionBar";

type TabKey = "importees" | "retouchees" | "animations";

const RETENTION_LABELS: Record<number, string> = {
  7: "7 jours",
  30: "30 jours",
  90: "3 mois",
};

function BibliothequeInner() {
  const { user: clerkUser, isLoaded: clerkLoaded } = useUser();
  const { getToken } = useClerkAuth();
  const isSignedIn = !!clerkUser;

  const params = useSearchParams();

  // ── États ──
  const [activeTab, setActiveTab] = useState<TabKey>("importees");
  const [libraryImages, setLibraryImages] = useState<LibraryImage[]>([]);
  const [history, setHistory] = useState<UserHistoryResponse | null>(null);
  const [loadingLib, setLoadingLib] = useState(true);
  const [loadingHist, setLoadingHist] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authToken, setAuthToken] = useState<string | null>(null);

  // Onglet Importées
  const [uploading, setUploading] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  // Onglets Retouchées / Animations
  const [deleting, setDeleting] = useState<string | null>(null);
  const [confirmDeleteAll, setConfirmDeleteAll] = useState(false);

  // ── Query param → initial tab ──
  useEffect(() => {
    const t = params.get("tab");
    if (t === "importees" || t === "retouchees" || t === "animations") {
      setActiveTab(t);
    }
  }, [params]);

  // ── Token JWT ──
  useEffect(() => {
    if (!isSignedIn) return;
    getToken().then((t) => setAuthToken(t || null)).catch(() => setAuthToken(null));
  }, [isSignedIn, getToken]);

  // ── Fetchs ──
  const fetchLibrary = useCallback(async () => {
    try {
      const data = await listLibrary(100);
      setLibraryImages(data.items);
    } catch {
      // Silencieux — erreur partielle
    } finally {
      setLoadingLib(false);
    }
  }, []);

  const fetchHistory = useCallback(async () => {
    try {
      const data = await getUserHistory();
      setHistory(data);
    } catch {
      // Silencieux
    } finally {
      setLoadingHist(false);
    }
  }, []);

  useEffect(() => {
    if (isSignedIn) {
      setLoadingLib(true);
      setLoadingHist(true);
      Promise.all([fetchLibrary(), fetchHistory()]);
    } else if (clerkLoaded) {
      setLoadingLib(false);
      setLoadingHist(false);
    }
  }, [isSignedIn, clerkLoaded, fetchLibrary, fetchHistory]);

  // ── Données dérivées par onglet ──
  const importeeItems = useMemo<ImporteeItem[]>(() => {
    const items: ImporteeItem[] = libraryImages.map((l) => ({ kind: "library", lib: l }));
    const libUrls = new Set(libraryImages.map((l) => l.url));
    const seen = new Set<string>(libUrls);
    for (const t of history?.travaux ?? []) {
      if (t.type === "animation") continue;
      const u = t.url_original;
      if (!u || seen.has(u)) continue;
      seen.add(u);
      items.push({ kind: "history", trav: t, url: u });
    }
    return items.sort((a, b) => {
      const da = a.kind === "library" ? a.lib.cree_le : a.trav.cree_le;
      const db = b.kind === "library" ? b.lib.cree_le : b.trav.cree_le;
      return db.localeCompare(da);
    });
  }, [libraryImages, history]);

  const retoucheesTravaux = useMemo(() =>
    (history?.travaux ?? []).filter((t) =>
      (t.type === "restauration" || t.type === "colorisation")
    ),
    [history]
  );

  const animationsTravaux = useMemo(() =>
    (history?.travaux ?? []).filter((t) => t.type === "animation"),
    [history]
  );

  const currentTabItems = activeTab === "importees"
    ? importeeItems
    : activeTab === "retouchees"
      ? retoucheesTravaux
      : animationsTravaux;

  // ── Handlers ──
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      for (let i = 0; i < files.length; i++) {
        await uploadToLibrary(files[i]);
      }
      await fetchLibrary();
    } catch {
      setError("Échec de l'import. Vérifiez le format (JPEG, PNG, WebP) et la taille (< 20 Mo).");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDeleteLib = async (id: string) => {
    try {
      await deleteLibraryImage(id);
      setLibraryImages((prev) => prev.filter((img) => img.id !== id));
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    } catch {
      setError("Échec de la suppression.");
    }
  };

  const handleDeleteHist = async (travailId: string) => {
    setDeleting(travailId);
    try {
      await deleteTravail(travailId);
      await fetchHistory();
    } catch {
      setError("Erreur lors de la suppression.");
    } finally {
      setDeleting(null);
    }
  };

  const handleDeleteAll = async () => {
    if (!confirmDeleteAll) {
      setConfirmDeleteAll(true);
      return;
    }
    setDeleting("__all__");
    try {
      await deleteAllHistory();
      setConfirmDeleteAll(false);
      await fetchHistory();
    } catch {
      setError("Erreur lors de la suppression.");
    } finally {
      setDeleting(null);
    }
  };

  const handleRetentionChange = async (jours: number) => {
    try {
      await updatePreferences(jours);
      await fetchHistory();
    } catch {
      setError("Erreur lors de la mise à jour.");
    }
  };

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectedCount = selected.size;
  const retention = history?.retention_jours || 30;
  const totalTravaux = history?.total || 0;

  // ── Loading global ──
  if (!clerkLoaded) {
    return (
      <div className="flex flex-col min-h-screen bg-background">
        <Navbar />
        <main className="flex-1 pt-28 pb-16 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-accent animate-spin" />
        </main>
        <Footer />
      </div>
    );
  }

  // ── Non connecté ──
  if (!isSignedIn) {
    return (
      <div className="flex flex-col min-h-screen bg-background">
        <Navbar />
        <main className="flex-1 pt-28 pb-16 flex items-center justify-center">
          <div className="text-center px-4">
            <Images className="w-16 h-16 text-muted mx-auto mb-4 opacity-50" />
            <h2 className="text-xl font-semibold text-foreground mb-2">
              Connectez-vous pour accéder à votre bibliothèque
            </h2>
            <p className="text-muted mb-6 max-w-md mx-auto">
              Importez, restaurez et animez vos photos dans votre galerie personnelle.
            </p>
            <Link
              href="/sign-in"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-accent text-white dark:text-gray-950 font-semibold hover:brightness-110 transition-all"
            >
              Se connecter
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  const isLoading = loadingLib || loadingHist;

  return (
    <div className="flex flex-col min-h-screen bg-background">
      <Navbar />
      <main className="flex-1 pt-24 pb-16">
        {/* Background */}
        <div className="fixed inset-0 pointer-events-none">
          <div className="absolute top-1/4 left-1/4 w-[600px] h-[600px] bg-violet-600/6 rounded-full blur-[120px]" />
          <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-accent/5 rounded-full blur-[100px]" />
        </div>

        <div className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6">
          {/* Header */}
          <div className="text-center mb-10">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-accent/10 border border-accent/20 text-accent text-sm font-medium mb-4">
              <Images className="w-4 h-4" />
              Ma bibliothèque
            </div>
            <h1 className="text-3xl sm:text-4xl font-bold text-foreground mb-3 font-[family-name:var(--font-playfair)]">
              Votre galerie <span className="text-gradient">personnelle</span>
            </h1>
            <p className="text-muted max-w-lg mx-auto">
              Retrouvez toutes vos photos importées, retouchées et animées au même endroit.
            </p>
          </div>

          {/* Tabs */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex justify-center mb-8"
          >
            <div className="inline-flex bg-card border border-card-border rounded-2xl p-1.5 gap-1">
              {([
                { key: "importees" as const, label: "Importées", icon: Upload },
                { key: "retouchees" as const, label: "Retouchées", icon: Sparkles },
                { key: "animations" as const, label: "Animations", icon: Film },
              ]).map(({ key, label, icon: Icon }) => (
                <button
                  key={key}
                  onClick={() => setActiveTab(key)}
                  className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    activeTab === key
                      ? "bg-accent text-white dark:text-gray-950 shadow-lg shadow-accent/20"
                      : "text-muted hover:text-foreground hover:bg-surface-alt"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </button>
              ))}
            </div>
          </motion.div>

          {/* Count */}
          {!isLoading && currentTabItems.length > 0 && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center text-xs text-muted mb-4"
            >
              {currentTabItems.length} élément{currentTabItems.length > 1 ? "s" : ""}
            </motion.p>
          )}

          {/* Toolbar — Onglet Importées */}
          {activeTab === "importees" && (
            <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
              <label className="inline-flex items-center gap-2 px-5 py-3 rounded-full bg-accent text-white dark:text-gray-950 font-semibold text-sm hover:brightness-110 transition-all cursor-pointer active:scale-[0.97]">
                {uploading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Upload className="w-4 h-4" />
                )}
                {uploading ? "Import..." : "Importer des images"}
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  multiple
                  className="hidden"
                  onChange={handleUpload}
                  disabled={uploading}
                />
              </label>

              {selectedCount > 0 && (
                <div className="flex items-center gap-3">
                  <span className="text-sm text-muted">
                    {selectedCount} sélectionnée{selectedCount > 1 ? "s" : ""}
                  </span>
                  <Link
                    href={`/restore?from=library&ids=${[...selected].join(",")}`}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-accent/30 text-accent hover:bg-accent/10 text-sm font-medium transition-all"
                  >
                    <Sparkles className="w-4 h-4" />
                    Restaurer la sélection
                  </Link>
                </div>
              )}
            </div>
          )}

          {/* Retention bar — Onglets Retouchées / Animations */}
          {activeTab !== "importees" && (
            <RetentionBar
              retentionJours={retention}
              onRetentionChange={handleRetentionChange}
              confirmDeleteAll={confirmDeleteAll}
              onDeleteAllClick={handleDeleteAll}
              deleting={deleting === "__all__"}
              onCancelDelete={() => setConfirmDeleteAll(false)}
              hasItems={currentTabItems.length > 0}
            />
          )}

          {/* Error */}
          {error && (
            <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-red-400 text-sm">{error}</p>
              <button
                onClick={() => setError(null)}
                className="ml-auto text-red-400/60 hover:text-red-400"
              >
                ✕
              </button>
            </div>
          )}

          {/* Content */}
          {isLoading ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
              {[...Array(10)].map((_, i) => (
                <div
                  key={i}
                  className="aspect-square rounded-xl bg-surface/60 animate-pulse"
                />
              ))}
            </div>
          ) : activeTab === "importees" ? (
            <ImporteesTab
              items={importeeItems}
              uploading={uploading}
              selected={selected}
              toggleSelect={toggleSelect}
              onUpload={handleUpload}
              onDeleteLib={handleDeleteLib}
              onDeleteHist={handleDeleteHist}
              deleting={deleting}
            />
          ) : activeTab === "retouchees" ? (
            <RetoucheesTab
              travaux={retoucheesTravaux}
              authToken={authToken}
              onDelete={handleDeleteHist}
              deleting={deleting}
            />
          ) : (
            <AnimationsTab
              travaux={animationsTravaux}
              authToken={authToken}
              onDelete={handleDeleteHist}
              deleting={deleting}
            />
          )}

          {/* Summary footer — historique uniquement */}
          {activeTab !== "importees" && currentTabItems.length > 0 && history && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center text-xs text-muted mt-8"
            >
              {totalTravaux} travail{totalTravaux > 1 ? "x" : ""} au total · Conservation : {RETENTION_LABELS[retention]} ·{" "}
              Les fichiers sont automatiquement supprimés après expiration.
            </motion.p>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}

export default function BibliothequeClient() {
  return (
    <Suspense fallback={
      <div className="flex flex-col min-h-screen bg-background">
        <Navbar />
        <main className="flex-1 pt-28 pb-16 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-accent animate-spin" />
        </main>
        <Footer />
      </div>
    }>
      <BibliothequeInner />
    </Suspense>
  );
}
