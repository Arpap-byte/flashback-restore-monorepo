"use client";

import type { Metadata } from 'next';
import { useState, useEffect, useCallback, useRef } from "react";

export const metadata: Metadata = {
  title: 'Animer une photo — Flashback Restore',
  description: 'Donnez vie à vos photos avec l\'animation IA. Transformez un portrait en vidéo réaliste.',
  openGraph: { images: ['/og-default.jpg'] },
};
import { useRouter } from "next/navigation";
import Image from "next/image";
import { motion } from "framer-motion";
import { useAuth } from "@/context/AuthContext";
import { useUser } from "@clerk/nextjs";
import {
  Sparkles, AlertTriangle, X, Download, Play,
  RefreshCw, Film, Heart, Smile, Eye, Wind,
  Hand, Clock, Monitor,
} from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { animatePhoto, checkAnimationStatus, getPhotoUrlAsync, AnimationStatus, ApiError } from "@/lib/api";

const POLL_TIMEOUT = 600_000; // 10 minutes
const POLL_DELAYS = [5_000, 8_000, 12_000, 20_000, 30_000];

const COMPORTEMENTS = [
  { id: "naturel", label: "Naturel", icon: Heart, desc: "Micro-expressions douces, respiration calme" },
  { id: "sourire", label: "Sourire", icon: Smile, desc: "Un sourire chaleureux qui s'installe" },
  { id: "rire", label: "Rire léger", icon: Sparkles, desc: "Un petit rire spontané et joyeux" },
  { id: "respirer", label: "Respiration", icon: Wind, desc: "Respiration visible, présence vivante" },
  { id: "clin_oeil", label: "Clin d'œil", icon: Eye, desc: "Un clin d'œil complice et naturel" },
  { id: "salut", label: "Salut", icon: Hand, desc: "Un signe de tête et sourire pour dire bonjour" },
];

export default function AnimatePage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const { user: clerkUser, isLoaded: clerkLoaded } = useUser();
  const isAuthenticated = !!user || !!clerkUser;
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [comportement, setComportement] = useState("naturel");
  const [resolution, setResolution] = useState("720p"); // 720p par défaut
  const [animating, setAnimating] = useState(false);
  const [travailId, setTravailId] = useState<string | null>(null);
  const [status, setStatus] = useState<AnimationStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [videoUrl, setVideoUrl] = useState<string | null>(null); // URL avec token JWT pour <video>
  const pollRef = useRef<NodeJS.Timeout | null>(null);
  const pollAttempts = useRef(0);
  const pollStartTime = useRef(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
        try {
          const res = await fetch(url);
          if (!res.ok) {
            // Token expiré ou accès refusé → on ne peut pas charger l'image
            // L'aperçu reste affiché (chargé avant tentative de fetch via setPreview)
            if (process.env.NODE_ENV === "development") {
              console.error("Impossible de charger la photo pour animation:", res.status);
            }
            return;
          }
          const blob = await res.blob();
          setFile(new File([blob], "photo.jpg", { type: "image/jpeg" }));
        } catch {}
      })();
    }
  }, []);

  useEffect(() => {
    if (!travailId || status?.status === "termine" || status?.status === "erreur") return;
    if (pollAttempts.current === 0) pollStartTime.current = Date.now();

    let cancelled = false;
    const poll = async () => {
      if (cancelled) return;
      const elapsed = Date.now() - pollStartTime.current;
      if (elapsed >= POLL_TIMEOUT) {
        setStatus({ status: "erreur", message: "L'animation a pris trop de temps. Veuillez réessayer." });
        return;
      }
      try {
        const result = await checkAnimationStatus(travailId);
        if (cancelled) return;
        setStatus(result);
        if (result.status === "termine" || result.status === "erreur") return;
        const delay = POLL_DELAYS[Math.min(pollAttempts.current, POLL_DELAYS.length - 1)];
        pollAttempts.current += 1;
        pollRef.current = setTimeout(poll, delay);
      } catch (err) {
        if (cancelled) return;
        // F6: Arrêter le polling sur les erreurs d'authentification (401/403)
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          setStatus({ status: "erreur", message: err.message || "Session expirée. Veuillez vous reconnecter." });
          return;
        }
        // Erreur réseau temporaire : on continue le polling
        const delay = POLL_DELAYS[Math.min(pollAttempts.current, POLL_DELAYS.length - 1)];
        pollAttempts.current += 1;
        pollRef.current = setTimeout(poll, delay);
      }
    };
    poll();
    return () => { cancelled = true; if (pollRef.current) clearTimeout(pollRef.current); };
  }, [travailId, status?.status]);

  // F2: Convertir url_video en URL avec token JWT (balise <video> ne peut pas envoyer de header Authorization)
  useEffect(() => {
    let cancelled = false;
    if (status?.url_video) {
      getPhotoUrlAsync(status.url_video).then((url) => {
        if (!cancelled) setVideoUrl(url);
      });
    } else {
      setVideoUrl(null);
    }
    return () => { cancelled = true; };
  }, [status?.url_video]);

  const handleFile = useCallback((f: File) => {
    if (!["image/jpeg", "image/png", "image/webp"].includes(f.type)) {
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
    setStatus(null);
    setTravailId(null);
    setFile(f);
    const reader = new FileReader();
    reader.onloadend = () => setPreview(reader.result as string);
    reader.readAsDataURL(f);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
  }, [handleFile]);

  const handleAnimate = async () => {
    if (!file) return;
    setAnimating(true);
    setError(null);
    setStatus({ status: "en_attente" });
    pollAttempts.current = 0;
    pollStartTime.current = 0;
    try {
      const result = await animatePhoto(file, comportement, resolution);
      setTravailId(result.travail_id);
      setStatus({ status: "en_cours" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors du lancement de l'animation.");
      setStatus(null);
    } finally {
      setAnimating(false);
    }
  };

  const handleClear = () => {
    setFile(null); setPreview(null); setStatus(null);
    setTravailId(null); setError(null); setComportement("naturel"); setResolution("720p");
    setVideoUrl(null);
    pollAttempts.current = 0; pollStartTime.current = 0;
    sessionStorage.removeItem("flashback_photo");
    if (pollRef.current) clearTimeout(pollRef.current);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  if (authLoading || !clerkLoaded) {
    return (
      <div className="min-h-screen bg-background"><Navbar />
        <main className="pt-24 pb-16 flex items-center justify-center">
          <div className="w-12 h-12 rounded-full border-2 border-violet-500/30 border-t-violet-500 animate-spin" />
        </main><Footer />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-background"><Navbar />
        <main className="pt-24 pb-16 flex items-center justify-center text-center px-4">
          <div>
            <Film className="w-16 h-16 text-muted mx-auto mb-4 opacity-50" />
            <h2 className="text-xl font-semibold text-foreground mb-2">Connectez-vous pour animer vos photos</h2>
            <p className="text-muted mb-6 max-w-md">Donnez vie à vos souvenirs avec des expressions naturelles.</p>
            <a href="/auth?callbackUrl=/animate" className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-accent text-white dark:text-gray-950 font-semibold hover:brightness-110 transition-all">
              Se connecter
            </a>
          </div>
        </main><Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="pt-24 pb-16">
        <div className="fixed inset-0 pointer-events-none">
          <div className="absolute top-1/3 left-1/3 w-[600px] h-[600px] bg-violet-600/8 rounded-full blur-[120px]" />
          <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-accent/5 rounded-full blur-[100px]" />
        </div>

        <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-10">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-400 text-sm font-medium mb-6">
              <Film className="w-4 h-4" /> Étape 3 — Animation
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-4 font-[family-name:var(--font-playfair)]">
              Donnez vie à<br /><span className="text-gradient">votre souvenir</span>
            </h1>
            <p className="text-muted text-lg max-w-xl mx-auto">
              Des micro-expressions naturelles qui donnent vie à votre photo. Pas de parole — juste des comportements authentiques.
            </p>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
            {!preview ? (
              <>
              <div
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`relative rounded-3xl border-2 border-dashed p-12 lg:p-16 text-center cursor-pointer transition-all duration-300 ${
                  dragOver ? "border-violet-400 bg-violet-500/5 scale-[1.01]" : "border-card-border hover:border-muted bg-card/50"
                }`}
              >
                <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden"
                  onChange={(e) => { if (e.target.files?.[0]) handleFile(e.target.files[0]); }} />
                <div className="flex flex-col items-center gap-4">
                  <div className="w-20 h-20 rounded-2xl bg-violet-500/10 flex items-center justify-center">
                    <Film className="w-10 h-10 text-violet-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-foreground mb-1">Glissez une photo ici</h3>
                    <p className="text-muted text-sm">ou cliquez pour sélectionner — JPG, PNG, WebP, max 20 Mo</p>
                  </div>
                </div>
              </div>
              <p className="text-center text-sm text-muted mt-4">
                📸 Vous pouvez aussi <a href="/restore" className="text-accent hover:underline">restaurer une photo</a> d'abord, puis revenir l'animer.
              </p>
              </>
            ) : (
              <div className="grid lg:grid-cols-5 gap-8">
                <div className="lg:col-span-2">
                  <div className="relative rounded-2xl overflow-hidden border border-card-border bg-card shadow-xl aspect-[3/4]">
                    <Image src={preview} alt="Aperçu" fill unoptimized className="object-contain" sizes="(max-width: 1024px) 100vw, 40vw" />
                    {!animating && !status && (
                      <button onClick={handleClear} className="absolute top-3 right-3 w-8 h-8 rounded-full bg-black/50 backdrop-blur text-white flex items-center justify-center hover:bg-black/70">
                        <X className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>

                <div className="lg:col-span-3 flex flex-col gap-6">
                  {!animating && !status && (
                    <>
                      <div className="bg-card border border-card-border rounded-2xl p-6">
                        <div className="flex items-center gap-2 mb-4">
                          <Sparkles className="w-4 h-4 text-violet-400" />
                          <span className="text-sm font-semibold text-foreground">Choisissez un comportement</span>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          {COMPORTEMENTS.map((c) => (
                            <button
                              key={c.id}
                              onClick={() => setComportement(c.id)}
                              className={`p-4 rounded-xl border-2 text-left transition-all ${
                                comportement === c.id
                                  ? "border-violet-500 bg-violet-500/10 shadow-lg shadow-violet-500/10"
                                  : "border-card-border hover:border-violet-500/30 hover:bg-violet-500/5"
                              }`}
                            >
                              <c.icon className={`w-5 h-5 mb-2 ${comportement === c.id ? "text-violet-400" : "text-muted"}`} />
                              <p className="text-sm font-semibold text-foreground">{c.label}</p>
                              <p className="text-xs text-muted mt-1">{c.desc}</p>
                            </button>
                          ))}
                        </div>
                      </div>

                      <div className="bg-violet-500/5 border border-violet-500/10 rounded-xl p-4">
                        <p className="text-sm text-muted flex items-start gap-2">
                          <Sparkles className="w-4 h-4 text-violet-400 flex-shrink-0 mt-0.5" />
                          Animation sans parole — micro-expressions naturelles en ~5 secondes. Résultat vidéo MP4.
                        </p>
                      </div>

                      <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4">
                        <p className="text-sm text-muted flex items-start gap-2">
                          <Clock className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                          La création de l&apos;animation peut prendre <strong>2 à 3 minutes</strong>. Le temps dépend du service d&apos;animation et de la photo.
                        </p>
                      </div>

                      {/* Toggle 1080p */}
                      <div className="bg-card border border-card-border rounded-xl p-4">
                        <label className="flex items-center gap-3 cursor-pointer">
                          <Monitor className="w-5 h-5 text-muted" />
                          <div className="flex-1">
                            <p className="text-sm font-semibold text-foreground">Qualité 1080p</p>
                            <p className="text-xs text-muted">Haute définition — <strong>20 crédits</strong> (au lieu de 10)</p>
                          </div>
                          <button
                            type="button"
                            role="switch"
                            aria-checked={resolution === "1080p"}
                            onClick={() => setResolution(resolution === "1080p" ? "720p" : "1080p")}
                            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                              resolution === "1080p" ? "bg-violet-500" : "bg-muted/30"
                            }`}
                          >
                            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                              resolution === "1080p" ? "translate-x-6" : "translate-x-1"
                            }`} />
                          </button>
                        </label>
                      </div>

                      <button
                        onClick={handleAnimate}
                        className="w-full inline-flex items-center justify-center gap-2 px-6 py-4 rounded-full bg-gradient-to-r from-violet-500 to-violet-600 text-white font-semibold text-base hover:brightness-110 hover:shadow-xl hover:shadow-violet-500/25 transition-all active:scale-[0.97]"
                      >
                        <Play className="w-5 h-5" /> Créer l&apos;animation
                      </button>
                    </>
                  )}

                  {status && (
                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                      <div className="bg-card border border-card-border rounded-2xl p-6">
                        <div className="flex items-center justify-between mb-3">
                          <h3 className="font-semibold text-foreground">
                            {status.status === "termine" ? "✨ Animation terminée !" :
                             status.status === "erreur" ? "Erreur" : "Création en cours..."}
                          </h3>
                          <span className="text-sm text-muted">{Math.round(status.progress || (status.status === "termine" ? 100 : status.status === "en_cours" ? 60 : 20))}%</span>
                        </div>
                        <div className="w-full h-2 bg-surface rounded-full overflow-hidden mb-2">
                          <div className={`h-full rounded-full transition-all duration-1000 ${
                            status.status === "termine" ? "bg-emerald-400" : status.status === "erreur" ? "bg-red-400" : "bg-violet-400"
                          }`} style={{ width: `${status.status === "termine" ? 100 : status.status === "en_cours" ? 60 : 20}%` }} />
                        </div>
                        <div className="flex justify-between text-xs text-muted">
                          <span>Envoi</span><span>Traitement</span><span>Terminé</span>
                        </div>
                      </div>

                      {status.status === "termine" && videoUrl && (
                        <div className="space-y-3">
                          <video src={videoUrl} controls className="w-full rounded-xl" />
                          <div className="flex gap-3">
                            <button onClick={() => window.open(videoUrl!, "_blank")} className="flex-1 py-3 rounded-full bg-accent text-white dark:text-gray-950 font-medium text-sm hover:brightness-110 flex items-center justify-center gap-2">
                              <Download className="w-4 h-4" /> Télécharger
                            </button>
                            <button onClick={handleClear} className="px-6 py-3 rounded-full border border-card-border text-muted hover:text-foreground text-sm flex items-center gap-2">
                              <RefreshCw className="w-4 h-4" /> Nouvelle
                            </button>
                          </div>
                        </div>
                      )}

                      {status.status === "erreur" && (
                        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
                          <AlertTriangle className="w-4 h-4 inline mr-2" />
                          {status.message || "Une erreur est survenue."}
                          <button onClick={handleClear} className="block mt-2 text-violet-400 hover:underline">Réessayer avec une autre photo</button>
                        </div>
                      )}
                    </motion.div>
                  )}
                </div>
              </div>
            )}

            {error && (
              <div className="flex items-center gap-2 justify-center mt-6 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm max-w-lg mx-auto">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />{error}
              </div>
            )}
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
