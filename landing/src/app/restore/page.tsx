"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload,
  Sparkles,
  ArrowRight,
  AlertTriangle,
  Shield,
  LogIn,
  X,
  Download,
  Play,
  RefreshCw,
  Image as ImageIcon,
  ArrowLeftRight,
  Zap,
  Palette,
  Loader2,
  Check,
} from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { useAuth } from "@/context/AuthContext";
import { useUser } from "@clerk/nextjs";
import { useSearchParams } from "next/navigation";
import { restorePhoto, colorizePhoto, getPhotoUrlAsync, RestoreResult, pollRestoreJob } from "@/lib/api";

function getCreditTotal(resolution: string, colorize: boolean): number {
  const base = resolution === "4k" ? 4 : resolution === "1080p" ? 2 : 1;
  const colorExtra = resolution === "4k" ? 4 : resolution === "1080p" ? 2 : 1;
  return base + (colorize ? colorExtra : 0);
}

function Label({ icon: Icon, label }: { icon: React.ComponentType<{ className?: string }>, label: string }) {
  return (
    <div className="flex items-center gap-2">
      <Icon className="w-4 h-4 text-accent" />
      <span className="text-sm font-medium text-foreground">{label}</span>
    </div>
  );
}

export default function RestorePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading: authLoading } = useAuth();
  const { user: clerkUser, isLoaded: clerkLoaded } = useUser();
  const isAuthenticated = !!user || !!clerkUser;
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [restoring, setRestoring] = useState(false);
  const [restoreResult, setRestoreResult] = useState<RestoreResult | null>(
    null
  );
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [showAfter, setShowAfter] = useState(true);
  const [compareMode, setCompareMode] = useState(false);
  const [sliderPos, setSliderPos] = useState(50);
  const [colorize, setColorize] = useState(false);
  const [resolution, setResolution] = useState<"720p" | "1080p" | "4k">("720p");
  const [colorizing, setColorizing] = useState(false);
  const [restoreProgress, setRestoreProgress] = useState<string>("");
  const [restoredUrl, setRestoredUrl] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Nettoyer l'AbortController au démontage du composant (F5)
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  // Calculer l'URL restaurée avec le token JWT (getPhotoUrlAsync récupère le token automatiquement)
  useEffect(() => {
    let cancelled = false;
    if (restoreResult?.url_image) {
      getPhotoUrlAsync(restoreResult.url_image).then((url) => {
        if (!cancelled) setRestoredUrl(url || null);
      });
    } else {
      setRestoredUrl(null);
    }
    return () => { cancelled = true; };
  }, [restoreResult]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const sliderRef = useRef<HTMLDivElement>(null);

  // On mount, check for photo passed from upload page or historique
  useEffect(() => {
    const stored = sessionStorage.getItem("flashback_photo");
    if (stored) {
      (async () => {
        // Si l'URL ne contient pas déjà un token JWT, on en ajoute un
        let url = stored;
        if (!url.includes("?token=") && url.includes("/uploads/")) {
          url = await getPhotoUrlAsync(url);
        }
        setPreview(url);
        // Convert URL to File for API call
        try {
          const res = await fetch(url);
          const blob = await res.blob();
          const f = new File([blob], "photo.jpg", { type: "image/jpeg" });
          setFile(f);
        } catch {}
      })();
    }
    // Si on vient depuis l'historique avec ?tab=colorize, pré-cocher la colorisation
    if (searchParams.get("tab") === "colorize") {
      setColorize(true);
    }
  }, [searchParams]);

  // Auto-restauration quand on vient de l'historique avec ?tab=colorize
  const hasAutoRestored = useRef(false);
  useEffect(() => {
    if (
      file &&
      !restoreResult &&
      !restoring &&
      searchParams.get("tab") === "colorize" &&
      !hasAutoRestored.current
    ) {
      hasAutoRestored.current = true;
      setColorize(true);
      // Petit délai pour que l'UI s'affiche avant le traitement
      const timer = setTimeout(() => {
        handleRestore();
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [file, restoreResult, restoring, searchParams]);

  // Colorisation directe depuis l'historique (?mode=colorize-only)
  const hasAutoColorized = useRef(false);
  useEffect(() => {
    if (
      file &&
      !restoreResult &&
      !colorizing &&
      searchParams.get("mode") === "colorize-only" &&
      !hasAutoColorized.current
    ) {
      hasAutoColorized.current = true;
      // Petit délai pour que l'UI s'affiche avant le traitement
      const timer = setTimeout(() => {
        handleColorizeDirect();
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [file, restoreResult, colorizing, searchParams]);

  const handleFile = useCallback((f: File) => {
    const validTypes = ["image/jpeg", "image/png", "image/webp"];
    if (!validTypes.includes(f.type)) {
      setError("Format non supporté. Utilisez JPG, PNG ou WebP.");
      setTimeout(() => setError(null), 6000);
      return;
    }
    if (f.size > 20 * 1024 * 1024) {
      setError("Fichier trop volumineux (max 20 Mo).");
      setTimeout(() => setError(null), 6000);
      return;
    }
    setError(null);
    setRestoreResult(null);
    setRestoreProgress("");
    setFile(f);
    const reader = new FileReader();
    reader.onloadend = () => setPreview(reader.result as string);
    reader.readAsDataURL(f);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile]
  );

  const handleRestore = async () => {
    if (!file) return;
    // F5: Créer un AbortController pour pouvoir annuler le polling
    const controller = new AbortController();
    abortControllerRef.current = controller;
    setRestoring(true);
    setError(null);
    setRestoreProgress("Envoi de la photo...");
    try {
      const { jobId, travailId } = await restorePhoto(file, colorize, resolution);
      
      // Poll for the async job result
      setRestoreProgress("Restauration IA en cours...");
      const finalResult = await pollRestoreJob(jobId, (progress) => {
        setRestoreProgress(progress);
      }, 120000, controller.signal);
      
      setRestoreResult(finalResult);
      setRestoreProgress("");
    } catch (err) {
      // Ignorer les erreurs d'annulation (composant démonté)
      if (err instanceof Error && err.message === "Polling annulé.") return;
      setError(
        err instanceof Error
          ? err.message
          : "Erreur lors de la restauration. Veuillez réessayer."
      );
      setTimeout(() => setError(null), 6000);
    } finally {
      setRestoring(false);
      abortControllerRef.current = null;
    }
  };

  const handleClear = () => {
    // F5: Annuler tout polling en cours
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setFile(null);
    setPreview(null);
    setRestoreResult(null);
    setError(null);
    setRestoreProgress("");
    sessionStorage.removeItem("flashback_photo");
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleColorize = async () => {
    if (!file || !restoreResult || !restoredUrl) return;
    setColorizing(true);
    setError(null);
    try {
      // Fetch the restored image as a File (URL already includes token from useEffect)
      let res = await fetch(restoredUrl);
      // F8: Si l'URL avec token a expiré, rafraîchir le token
      if (!res.ok && (res.status === 401 || res.status === 403)) {
        const freshUrl = await getPhotoUrlAsync(restoreResult.url_image);
        res = await fetch(freshUrl);
      }
      // F7: Vérifier que la réponse est OK avant de lire le blob (évite d'envoyer un blob d'erreur HTML à colorizePhoto)
      if (!res.ok) {
        throw new Error(`Impossible de récupérer l'image restaurée (${res.status}).`);
      }
      const blob = await res.blob();
      const f = new File([blob], "restored.jpg", { type: "image/jpeg" });
      const result = await colorizePhoto(f);
      setRestoreResult(result);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Erreur lors de la colorisation. Veuillez réessayer."
      );
      setTimeout(() => setError(null), 6000);
    } finally {
      setColorizing(false);
    }
  };

  // Colorisation standalone (depuis l'historique, sans re-restauration)
  const handleColorizeDirect = async () => {
    if (!file) return;
    setColorizing(true);
    setError(null);
    setRestoreProgress("Colorisation en cours...");
    try {
      const result = await colorizePhoto(file);
      setRestoreResult(result);
      setRestoreProgress("");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Erreur lors de la colorisation. Veuillez réessayer."
      );
      setRestoreProgress("");
      setTimeout(() => setError(null), 6000);
    } finally {
      setColorizing(false);
    }
  };

  // Download handler
  const handleDownload = async (url: string, name: string) => {
    try {
      const res = await fetch(url);
      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
    } catch {
      setError("Erreur lors du téléchargement.");
      setTimeout(() => setError(null), 4000);
    }
  };

  // Loading skeleton
  if (authLoading || !clerkLoaded) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <main className="pt-24 lg:pt-32 pb-20 px-4">
          <div className="max-w-5xl mx-auto text-center">
            <div className="w-16 h-16 rounded-full border-4 border-accent/30 border-t-accent animate-spin mx-auto mb-6" />
            <p className="text-muted">Chargement...</p>
          </div>
        </main>
      </div>
    );
  }

  // Not authenticated = prompt
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <main className="pt-24 lg:pt-32 pb-20 px-4">
          <div className="max-w-lg mx-auto text-center">
            <div className="w-20 h-20 rounded-2xl bg-accent/10 flex items-center justify-center mx-auto mb-6">
              <LogIn className="w-10 h-10 text-accent" />
            </div>
            <h1 className="text-2xl font-bold text-foreground mb-3">
              Connectez-vous pour restaurer vos photos
            </h1>
            <p className="text-muted mb-8">
              Créez un compte gratuit pour commencer à restaurer vos souvenirs.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Link
                href="/auth?callbackUrl=/restore"
                className="px-6 py-3 rounded-full bg-accent text-white dark:text-gray-950 font-semibold hover:brightness-110 transition-all"
              >
                Se connecter
              </Link>
              <Link
                href="/auth?callbackUrl=/restore"
                className="px-6 py-3 rounded-full border border-card-border text-foreground hover:bg-surface transition-all"
              >
                Créer un compte
              </Link>
            </div>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="pt-24 lg:pt-32 pb-20 px-4">
        <div className="max-w-5xl mx-auto">
          {/* Header */}
          <div className="text-center mb-10">
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-4 font-[family-name:var(--font-playfair)]">
              Restaurez vos{" "}
              <span className="text-gradient">photos anciennes</span>
            </h1>
            <p className="text-muted max-w-xl mx-auto">
              Notre IA détecte et répare automatiquement les défauts, rayures et taches.
              Résultat instantané.
            </p>
          </div>

          {/* Upload zone */}
          {!preview && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className={`max-w-2xl mx-auto border-2 border-dashed rounded-3xl p-12 text-center transition-all cursor-pointer ${
                dragOver
                  ? "border-accent bg-accent/5 scale-[1.02]"
                  : "border-card-border hover:border-accent/30 hover:bg-surface/50"
              }`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleFile(f);
                }}
                className="hidden"
              />
              <div className="w-16 h-16 rounded-2xl bg-accent/10 flex items-center justify-center mx-auto mb-4">
                <Upload className="w-8 h-8 text-accent" />
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">
                Glissez votre photo ici
              </h3>
              <p className="text-muted text-sm mb-4">
                ou cliquez pour sélectionner un fichier
              </p>
              <p className="text-muted/60 text-xs">
                JPG, PNG, WebP — Max 20 Mo
              </p>
            </motion.div>
          )}

          {/* Photo loaded + result */}
          {preview && (
            <div className="max-w-4xl mx-auto">
              {/* Panneau d'options de traitement */}
              {!restoreResult && !restoring && (
                <div className="max-w-xl mx-auto mb-6">
                  {/* Photo preview */}
                  <div className="relative w-full rounded-2xl overflow-hidden bg-surface border border-card-border mb-4">
                    <Image
                      src={preview}
                      alt="Photo à restaurer"
                      width={800}
                      height={600}
                      className="w-full h-auto object-contain"
                      unoptimized
                    />
                  </div>

                  {/* Options */}
                  <div className="bg-card border border-card-border rounded-2xl p-5 space-y-5">
                    {/* Résolution */}
                    <div>
                      <Label icon={Zap} label="Résolution" />
                      <div className="grid grid-cols-3 gap-2 mt-2">
                        {([
                          { key: "720p" as const, label: "720p", credits: 1, desc: "Standard" },
                          { key: "1080p" as const, label: "1080p", credits: 2, desc: "Haute déf." },
                          { key: "4k" as const, label: "4K", credits: 4, desc: "Ultra HD" },
                        ]).map(({ key, label, credits, desc }) => (
                          <button
                            key={key}
                            onClick={() => setResolution(key)}
                            className={`p-3 rounded-xl border text-center transition-all ${
                              resolution === key
                                ? "border-accent bg-accent/10 text-accent"
                                : "border-card-border text-muted hover:border-accent/30"
                            }`}
                          >
                            <div className="text-sm font-semibold">{label}</div>
                            <div className="text-xs text-muted">{desc}</div>
                            <div className="text-xs mt-1 font-medium">
                              {credits} crédit{credits > 1 ? "s" : ""}
                            </div>
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Colorisation */}
                    <div>
                      <Label icon={Palette} label="Colorisation" />
                      <button
                        onClick={() => setColorize(!colorize)}
                        className={`w-full mt-2 p-3 rounded-xl border text-left transition-all flex items-center justify-between ${
                          colorize
                            ? "border-orange-400 bg-orange-400/10 text-orange-400"
                            : "border-card-border text-muted hover:border-orange-400/30"
                        }`}
                      >
                        <div>
                          <div className="text-sm font-semibold">
                            {colorize ? "Colorisation activée" : "Ajouter la colorisation"}
                          </div>
                          <div className="text-xs text-muted">
                            +{resolution === "4k" ? "4" : resolution === "1080p" ? "2" : "1"} crédit{resolution === "4k" || resolution === "1080p" ? "s" : ""}
                          </div>
                        </div>
                        <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                          colorize ? "border-orange-400 bg-orange-400" : "border-card-border"
                        }`}>
                          {colorize && <Check className="w-3 h-3 text-white" />}
                        </div>
                      </button>
                    </div>

                    {/* Récapitulatif */}
                    <div className="bg-surface rounded-xl p-3 flex items-center justify-between">
                      <span className="text-sm text-muted">Total</span>
                      <span className="text-sm font-semibold text-foreground">
                        {getCreditTotal(resolution, colorize)} crédit{getCreditTotal(resolution, colorize) > 1 ? "s" : ""}
                      </span>
                    </div>
                  </div>

                  {/* Boutons */}
                  <div className="flex gap-3 mt-4 justify-center">
                    <button
                      onClick={handleClear}
                      className="px-5 py-2.5 rounded-full border border-card-border text-muted hover:text-foreground text-sm transition-all"
                    >
                      <X className="w-4 h-4 inline mr-1.5" />
                      Annuler
                    </button>
                    <button
                      onClick={handleRestore}
                      className="px-6 py-2.5 rounded-full bg-accent text-white dark:text-gray-950 font-semibold text-sm hover:brightness-110 transition-all flex items-center gap-2"
                    >
                      <Sparkles className="w-4 h-4" />
                      Restaurer ({getCreditTotal(resolution, colorize)} crédit{getCreditTotal(resolution, colorize) > 1 ? "s" : ""})
                    </button>
                  </div>
                </div>
              )}

              {/* Processing in progress — unchanged */}
              {(restoring || colorizing) && !restoreResult ? (
                /* Processing in progress */
                <div className="flex flex-col items-center py-12">
                  <div className="w-20 h-20 relative mb-6">
                    <div className="absolute inset-0 rounded-full border-4 border-accent/20" />
                    <div className="absolute inset-0 rounded-full border-4 border-accent border-t-transparent animate-spin" />
                  </div>
                  <p className="text-foreground font-medium text-lg mb-2">
                    {restoreProgress || "Restauration IA en cours..."}
                  </p>
                  <p className="text-muted text-sm">
                    Notre IA analyse et répare votre photo. Cela prend environ 30 secondes.
                  </p>
                </div>
              ) : restoreResult ? (
                /* Result displayed */
                <div className="space-y-6">
                  {/* Toggle buttons */}
                  <div className="flex items-center justify-center gap-2">
                    <button
                      onClick={() => { setShowAfter(false); setCompareMode(false); }}
                      className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                        !showAfter && !compareMode
                          ? "bg-accent text-white dark:text-gray-950"
                          : "bg-surface text-muted hover:text-foreground border border-card-border"
                      }`}
                    >
                      Avant
                    </button>
                    <button
                      onClick={() => { setShowAfter(true); setCompareMode(false); }}
                      className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                        showAfter && !compareMode
                          ? "bg-accent text-white dark:text-gray-950"
                          : "bg-surface text-muted hover:text-foreground border border-card-border"
                      }`}
                    >
                      ✨ Après
                    </button>
                    <button
                      onClick={() => { setShowAfter(true); setCompareMode(true); }}
                      className={`px-4 py-2 rounded-full text-sm font-medium transition-all flex items-center gap-1.5 ${
                        compareMode
                          ? "bg-accent text-white dark:text-gray-950"
                          : "bg-surface text-muted hover:text-foreground border border-card-border"
                      }`}
                    >
                      <ArrowLeftRight className="w-4 h-4" />
                      Comparer
                    </button>
                  </div>

                  {/* Comparison view */}
                  <div
                    ref={sliderRef}
                    className="relative w-full max-w-2xl mx-auto rounded-2xl overflow-hidden bg-surface border border-card-border select-none"
                  >
                    {/* Before image (always shown as background) */}
                    <Image
                      src={preview!}
                      alt="Photo originale"
                      width={800}
                      height={600}
                      className="w-full h-auto"
                      unoptimized
                    />

                    {/* After image overlay */}
                    {restoredUrl && (showAfter || compareMode) && (
                      <>
                        <div
                          className="absolute inset-0 overflow-hidden"
                          style={{
                            clipPath: compareMode
                              ? `inset(0 ${100 - sliderPos}% 0 0)`
                              : "inset(0 0 0 0)",
                          }}
                        >
                          <Image
                            src={restoredUrl!}
                            alt="Photo restaurée"
                            width={800}
                            height={600}
                            className="w-full h-full object-cover absolute inset-0"
                            unoptimized
                          />
                        </div>

                        {/* Slider handle — only in compare mode */}
                        {compareMode && (
                        <div
                          className="absolute top-0 bottom-0 w-1 bg-white shadow-lg cursor-ew-resize z-10"
                          style={{ left: `${sliderPos}%` }}
                          onMouseDown={(e) => {
                            e.preventDefault();
                            const slider = sliderRef.current;
                            if (!slider) return;
                            const rect = slider.getBoundingClientRect();

                            const onMove = (ev: MouseEvent) => {
                              const x = ev.clientX - rect.left;
                              const pct = Math.max(0, Math.min(100, (x / rect.width) * 100));
                              setSliderPos(pct);
                            };
                            const onUp = () => {
                              document.removeEventListener("mousemove", onMove);
                              document.removeEventListener("mouseup", onUp);
                            };
                            document.addEventListener("mousemove", onMove);
                            document.addEventListener("mouseup", onUp);
                          }}
                        >
                          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-10 h-10 bg-white rounded-full shadow-xl flex items-center justify-center">
                            <ArrowLeftRight className="w-5 h-5 text-gray-700" />
                          </div>
                        </div>
                        )}
                      </>
                    )}
                  </div>

                  {/* Labels */}
                  <div className="flex items-center justify-center gap-8 text-sm font-medium">
                    <span className="px-3 py-1 rounded-full bg-surface text-muted border border-card-border">
                      Avant
                    </span>
                    <span className="px-3 py-1 rounded-full bg-accent/15 text-accent">
                      ✨ Après
                    </span>
                  </div>

                  {/* Action buttons */}
                  <div className="flex flex-wrap items-center justify-center gap-3">
                    <button
                      onClick={() =>
                        restoredUrl &&
                        handleDownload(restoredUrl, "flashback-restored.jpg")
                      }
                      disabled={!restoredUrl}
                      className="px-5 py-2.5 rounded-full bg-accent/90 text-white dark:text-gray-950 text-sm font-medium hover:brightness-110 transition-all flex items-center gap-2 disabled:opacity-50"
                    >
                      <Download className="w-4 h-4" />
                      Télécharger la photo restaurée
                    </button>
                    {!colorize && (
                      <button
                        onClick={handleColorize}
                        disabled={colorizing}
                        className="px-5 py-2.5 rounded-full bg-orange-500 text-white text-sm font-medium hover:brightness-110 transition-all flex items-center gap-2 disabled:opacity-50"
                      >
                        {colorizing ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Palette className="w-4 h-4" />
                        )}
                        Coloriser
                      </button>
                    )}
                    <button
                      onClick={() => {
                        if (restoredUrl) {
                          sessionStorage.setItem("flashback_photo", restoredUrl);
                          router.push("/animate");
                        }
                      }}
                      disabled={!restoredUrl}
                      className="px-5 py-2.5 rounded-full border border-card-border text-foreground text-sm hover:bg-surface transition-all flex items-center gap-2 disabled:opacity-50"
                    >
                      <Play className="w-4 h-4" />
                      Animer cette photo
                    </button>
                    <button
                      onClick={handleClear}
                      className="px-5 py-2.5 rounded-full border border-card-border text-muted hover:text-foreground text-sm transition-all flex items-center gap-2"
                    >
                      <RefreshCw className="w-4 h-4" />
                      Nouvelle photo
                    </button>
                  </div>

                  {/* Analysis info */}
                  {restoreResult.analyse && (
                    <div className="max-w-xl mx-auto mt-6 p-4 bg-surface rounded-xl border border-card-border">
                      <h4 className="text-sm font-semibold text-foreground mb-2">
                        Analyse de l&apos;IA
                      </h4>
                      <div className="grid grid-cols-2 gap-2 text-xs text-muted">
                        <div>
                          <span className="text-foreground/70">État :</span>{" "}
                          {restoreResult.analyse.etat_global}
                        </div>
                        <div>
                          <span className="text-foreground/70">Âge estimé :</span>{" "}
                          {restoreResult.analyse.age_estime}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : null}

              {/* Error display */}
              {error && !restoreResult && (
                <div className="flex items-center gap-2 justify-center mt-6 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm max-w-lg mx-auto">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                  {error}
                </div>
              )}
            </div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
