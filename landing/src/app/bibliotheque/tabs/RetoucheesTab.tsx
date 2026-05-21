"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import {
  Trash2,
  RotateCw,
  Sparkles,
  ExternalLink,
  Film,
  Wand2,
  Clock,
  Calendar,
  Download,
} from "lucide-react";
import { TravailHistorique, getPhotoUrl, getPhotoUrlAsync } from "@/lib/api";

const TYPE_LABELS: Record<string, string> = {
  restauration: "Restauration",
  colorisation: "Colorisation",
};

const STATUT_COLORS: Record<string, string> = {
  termine: "text-emerald-400",
  en_cours: "text-amber-400",
  erreur: "text-red-400",
  cree: "text-muted",
};

const STATUT_LABELS: Record<string, string> = {
  termine: "Terminé",
  en_cours: "En cours",
  erreur: "Erreur",
  cree: "Créé",
};

function formatSize(octets: number | null): string {
  if (!octets) return "—";
  if (octets < 1024) return `${octets} o`;
  if (octets < 1024 * 1024) return `${(octets / 1024).toFixed(1)} Ko`;
  return `${(octets / (1024 * 1024)).toFixed(1)} Mo`;
}

function formatExpiration(iso: string | null): { text: string; urgent: boolean } {
  if (!iso) return { text: "—", urgent: false };
  const exp = new Date(iso);
  const now = new Date();
  const diffDays = Math.ceil((exp.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays <= 0) return { text: "Expiré", urgent: true };
  if (diffDays === 1) return { text: "Expire demain", urgent: true };
  if (diffDays <= 3) return { text: `${diffDays} jours`, urgent: true };
  if (diffDays <= 30) return { text: `${diffDays} jours`, urgent: false };
  return { text: `${Math.floor(diffDays / 30)} mois`, urgent: false };
}

function formatDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString("fr-FR", {
    day: "numeric", month: "long", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

interface RetoucheesTabProps {
  travaux: TravailHistorique[];
  authToken: string | null;
  onDelete: (id: string) => void;
  deleting: string | null;
}

export default function RetoucheesTab({
  travaux,
  authToken,
  onDelete,
  deleting,
}: RetoucheesTabProps) {
  if (travaux.length === 0) {
    return (
      <div className="text-center py-16">
        <Sparkles className="w-16 h-16 text-muted mx-auto mb-4 opacity-50" />
        <h3 className="text-lg font-semibold text-foreground mb-2">
          Aucune photo retouchée pour le moment
        </h3>
        <p className="text-muted mb-6">
          Restaurez votre première photo pour la voir apparaître ici.
        </p>
        <a
          href="/restore"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-accent text-white dark:text-gray-950 font-semibold hover:brightness-110 transition-all"
        >
          <Sparkles className="w-4 h-4" />
          Restaurer une photo
        </a>
      </div>
    );
  }

  return (
    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {travaux.map((t, i) => {
        const expiration = formatExpiration(t.expire_le);
        const photoUrl = t.url_resultat || t.url_original;
        const hasResult = t.url_resultat && t.statut === "termine";
        const isDeleting = deleting === t.id;

        return (
          <motion.div
            key={t.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="bg-card border border-card-border rounded-2xl overflow-hidden hover:border-accent/30 transition-all group relative"
          >
            {/* Photo preview */}
            {photoUrl && (
              <div className="aspect-[4/3] bg-surface-alt overflow-hidden relative">
                <Image
                  src={getPhotoUrl(photoUrl, authToken)}
                  alt={TYPE_LABELS[t.type] || t.type}
                  fill
                  unoptimized
                  className="object-contain group-hover:scale-105 transition-transform duration-500"
                  sizes="(max-width: 640px) 50vw, 33vw"
                />
                {/* Delete button overlay */}
                <button
                  onClick={() => onDelete(t.id)}
                  disabled={isDeleting}
                  className="absolute top-2 right-2 w-8 h-8 rounded-lg bg-black/50 backdrop-blur-sm flex items-center justify-center text-white/70 hover:text-red-400 hover:bg-black/70 opacity-0 group-hover:opacity-100 transition-all"
                  title="Supprimer"
                >
                  {isDeleting ? (
                    <RotateCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <Trash2 className="w-4 h-4" />
                  )}
                </button>
              </div>
            )}

            {/* Info */}
            <div className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-accent bg-accent/10 px-2 py-0.5 rounded-full flex items-center gap-1">
                  <Sparkles className="w-3 h-3" />
                  {TYPE_LABELS[t.type] || t.type}
                </span>
                <span className={`text-xs font-medium ${STATUT_COLORS[t.statut] || "text-muted"}`}>
                  {STATUT_LABELS[t.statut] || t.statut}
                </span>
              </div>

              <div className="flex items-center gap-1.5 text-xs text-muted mt-2">
                <Clock className="w-3 h-3" />
                {formatDate(t.cree_le)}
              </div>

              {/* Expiration */}
              <div className={`flex items-center gap-1.5 text-xs mt-1.5 ${
                expiration.urgent ? "text-amber-400" : "text-muted"
              }`}>
                <Calendar className="w-3 h-3" />
                {expiration.text === "—" ? "—" : `Expire : ${expiration.text}`}
              </div>

              {/* File sizes */}
              {(t.taille_original || t.taille_resultat) && (
                <div className="flex items-center gap-1.5 text-xs text-muted mt-1">
                  <Download className="w-3 h-3" />
                  {formatSize((t.taille_original || 0) + (t.taille_resultat || 0))}
                </div>
              )}

              {t.message_erreur && (
                <p className="text-xs text-red-400 mt-2 truncate">{t.message_erreur}</p>
              )}

              {/* Action buttons */}
              <div className="flex flex-wrap gap-1.5 mt-3">
                {hasResult && (
                  <a
                    href={getPhotoUrl(t.url_resultat!, authToken)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-accent/10 text-accent text-xs hover:bg-accent/20 transition-colors"
                  >
                    <ExternalLink className="w-3 h-3" />
                    Résultat
                  </a>
                )}
                <button
                  onClick={async () => {
                    const src = t.url_resultat || t.url_original;
                    if (src) {
                      const url = await getPhotoUrlAsync(src);
                      sessionStorage.setItem("flashback_photo", url);
                    }
                    window.location.href = "/animate";
                  }}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-violet-500/10 text-violet-400 text-xs hover:bg-violet-500/20 transition-colors"
                >
                  <Film className="w-3 h-3" />
                  Animer
                </button>
                {t.type === "restauration" && (
                  <button
                    onClick={async () => {
                      const src = t.url_resultat || t.url_original;
                      if (src) {
                        const url = await getPhotoUrlAsync(src);
                        sessionStorage.setItem("flashback_photo", url);
                      }
                      window.location.href = "/restore?mode=colorize-only";
                    }}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-amber-500/10 text-amber-400 text-xs hover:bg-amber-500/20 transition-colors"
                  >
                    <Wand2 className="w-3 h-3" />
                    Coloriser
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
