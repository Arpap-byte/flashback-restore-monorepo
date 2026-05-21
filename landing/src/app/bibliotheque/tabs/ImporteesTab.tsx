"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import {
  Upload,
  Trash2,
  Sparkles,
  Film,
  Loader2,
  ArrowRight,
} from "lucide-react";
import {
  LibraryImage,
  TravailHistorique,
  getPhotoUrl,
  getPhotoUrlAsync,
  deleteLibraryImage,
} from "@/lib/api";

export type ImporteeItem =
  | { kind: "library"; lib: LibraryImage }
  | { kind: "history"; trav: TravailHistorique; url: string };

interface ImporteesTabProps {
  items: ImporteeItem[];
  uploading: boolean;
  selected: Set<string>;
  toggleSelect: (id: string) => void;
  onUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onDeleteLib: (id: string) => void;
  onDeleteHist: (id: string) => void;
  deleting: string | null;
}

export default function ImporteesTab({
  items,
  uploading,
  selected,
  toggleSelect,
  onUpload,
  onDeleteLib,
  onDeleteHist,
  deleting,
}: ImporteesTabProps) {
  // Actions identiques à HistoriqueClient
  const handleRestoreHist = async (url: string) => {
    const fullUrl = await getPhotoUrlAsync(url);
    sessionStorage.setItem("flashback_photo", fullUrl);
    window.location.href = "/restore";
  };

  const handleAnimateHist = async (url: string) => {
    const fullUrl = await getPhotoUrlAsync(url);
    sessionStorage.setItem("flashback_photo", fullUrl);
    window.location.href = "/animate";
  };

  if (items.length === 0) {
    return (
      <div className="text-center py-16">
        <Upload className="w-16 h-16 text-muted mx-auto mb-4 opacity-40" />
        <h3 className="text-lg font-semibold text-foreground mb-2">
          Aucune image importée
        </h3>
        <p className="text-muted mb-6">
          Importez vos photos ou restaurez-en une pour la voir apparaître ici.
        </p>
        <Link
          href="/restore"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-accent text-white dark:text-gray-950 font-semibold hover:brightness-110 transition-all"
        >
          <Sparkles className="w-4 h-4" />
          Restaurer une photo
        </Link>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
      {items.map((item, i) => {
        const isLibrary = item.kind === "library";
        const id = isLibrary ? item.lib.id : item.trav.id;
        const url = isLibrary ? item.lib.url : item.url;
        const nomOrigine = isLibrary ? item.lib.nom_origine : null;
        const isSelected = selected.has(id);
        const isDeleting = deleting === id;
        const largeur = isLibrary ? item.lib.largeur : null;
        const hauteur = isLibrary ? item.lib.hauteur : null;

        return (
          <motion.div
            key={id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className={`group relative aspect-square rounded-xl overflow-hidden bg-surface border cursor-pointer transition-all ${
              isSelected
                ? "border-accent ring-2 ring-accent/30"
                : "border-card-border hover:border-muted"
            }`}
            onClick={() => {
              if (isLibrary) toggleSelect(id);
            }}
          >
            <Image
              src={getPhotoUrl(url)}
              alt={nomOrigine || "Image importée"}
              fill
              className="object-cover group-hover:scale-105 transition-transform duration-300"
              sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 20vw"
              unoptimized
            />

            {/* Overlay on hover */}
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100">
              {isLibrary ? (
                <>
                  <Link
                    href={`/restore?image=${encodeURIComponent(item.lib.url)}`}
                    className="p-2 rounded-full bg-accent text-white hover:brightness-110 transition-all"
                    onClick={(e) => e.stopPropagation()}
                    title="Restaurer"
                  >
                    <Sparkles className="w-4 h-4" />
                  </Link>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteLib(item.lib.id);
                    }}
                    className="p-2 rounded-full bg-red-500/80 text-white hover:bg-red-500 transition-all"
                    title="Supprimer"
                  >
                    {isDeleting ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRestoreHist(item.url);
                    }}
                    className="p-2 rounded-full bg-accent text-white hover:brightness-110 transition-all"
                    title="Restaurer"
                  >
                    <Sparkles className="w-4 h-4" />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleAnimateHist(item.url);
                    }}
                    className="p-2 rounded-full bg-violet-500/80 text-white hover:bg-violet-500 transition-all"
                    title="Animer"
                  >
                    <Film className="w-4 h-4" />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteHist(item.trav.id);
                    }}
                    className="p-2 rounded-full bg-red-500/80 text-white hover:bg-red-500 transition-all"
                    title="Supprimer"
                  >
                    {isDeleting ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                  </button>
                </>
              )}
            </div>

            {/* Selection check */}
            {isSelected && isLibrary && (
              <div className="absolute top-2 right-2 w-6 h-6 rounded-full bg-accent flex items-center justify-center">
                <Sparkles className="w-3 h-3 text-white" />
              </div>
            )}

            {/* History badge */}
            {!isLibrary && (
              <div className="absolute top-2 left-2 px-2 py-0.5 rounded-md bg-accent/80 text-white text-[10px] font-medium">
                Photo source
              </div>
            )}

            {/* Dimensions badge */}
            {largeur && hauteur && (
              <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded-md bg-black/60 text-white text-[10px]">
                {largeur}×{hauteur}
              </div>
            )}
          </motion.div>
        );
      })}
    </div>
  );
}
