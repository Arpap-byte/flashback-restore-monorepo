"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import {
  Upload,
  Image as ImageIcon,
  Trash2,
  Sparkles,
  ArrowRight,
  AlertTriangle,
  Loader2,
  Images,
} from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { useUser } from "@clerk/nextjs";
import {
  uploadToLibrary,
  listLibrary,
  deleteLibraryImage,
  getPhotoUrl,
  LibraryImage,
} from "@/lib/api";

export default function BibliothequeClient() {
  const { user, isSignedIn, isLoaded } = useUser();
  const [images, setImages] = useState<LibraryImage[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const fetchImages = async () => {
    try {
      setLoading(true);
      const data = await listLibrary();
      setImages(data.items);
    } catch (err) {
      setError("Impossible de charger la bibliothèque.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isSignedIn) fetchImages();
    else if (isLoaded) setLoading(false);
  }, [isSignedIn, isLoaded]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      for (let i = 0; i < files.length; i++) {
        await uploadToLibrary(files[i]);
      }
      await fetchImages();
    } catch (err) {
      setError("Échec de l'import. Vérifiez le format (JPEG, PNG, WebP) et la taille (< 20 Mo).");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteLibraryImage(id);
      setImages((prev) => prev.filter((img) => img.id !== id));
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    } catch {
      setError("Échec de la suppression.");
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

  if (!isLoaded) {
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
              Importez et gérez vos photos dans votre galerie personnelle.
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

  const selectedCount = selected.size;

  return (
    <div className="flex flex-col min-h-screen bg-background">
      <Navbar />
      <main className="flex-1 pt-24 pb-16">
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
              Images <span className="text-gradient">importées</span>
            </h1>
            <p className="text-muted max-w-lg mx-auto">
              Importez vos photos ici pour les utiliser plus tard dans vos
              restaurations et animations.
            </p>
          </div>

          {/* Upload + actions */}
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

          {/* Gallery grid */}
          {loading ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
              {[...Array(10)].map((_, i) => (
                <div
                  key={i}
                  className="aspect-square rounded-xl bg-surface/60 animate-pulse"
                />
              ))}
            </div>
          ) : images.length === 0 ? (
            <div className="text-center py-16">
              <ImageIcon className="w-16 h-16 text-muted mx-auto mb-4 opacity-40" />
              <p className="text-muted text-lg mb-2">Aucune image importée</p>
              <p className="text-muted/60 text-sm">
                Cliquez sur "Importer des images" pour commencer.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
              {images.map((img) => {
                const isSelected = selected.has(img.id);
                return (
                  <motion.div
                    key={img.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`group relative aspect-square rounded-xl overflow-hidden bg-surface border cursor-pointer transition-all ${
                      isSelected
                        ? "border-accent ring-2 ring-accent/30"
                        : "border-card-border hover:border-muted"
                    }`}
                    onClick={() => toggleSelect(img.id)}
                  >
                    <Image
                      src={getPhotoUrl(img.url)}
                      alt={img.nom_origine || "Image importée"}
                      fill
                      className="object-cover group-hover:scale-105 transition-transform duration-300"
                      sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 20vw"
                      unoptimized
                    />

                    {/* Overlay on hover */}
                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100">
                      <Link
                        href={`/restore?image=${encodeURIComponent(img.url)}`}
                        className="p-2 rounded-full bg-accent text-white hover:brightness-110 transition-all"
                        onClick={(e) => e.stopPropagation()}
                        title="Restaurer"
                      >
                        <Sparkles className="w-4 h-4" />
                      </Link>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(img.id);
                        }}
                        className="p-2 rounded-full bg-red-500/80 text-white hover:bg-red-500 transition-all"
                        title="Supprimer"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>

                    {/* Selection check */}
                    {isSelected && (
                      <div className="absolute top-2 right-2 w-6 h-6 rounded-full bg-accent flex items-center justify-center">
                        <Sparkles className="w-3 h-3 text-white" />
                      </div>
                    )}

                    {/* Dimensions badge */}
                    {img.largeur && img.hauteur && (
                      <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded-md bg-black/60 text-white text-[10px]">
                        {img.largeur}×{img.hauteur}
                      </div>
                    )}
                  </motion.div>
                );
              })}
            </div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
