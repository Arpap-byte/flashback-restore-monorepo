"use client";

import { useState } from "react";
import {
  ShieldCheck,
  ChevronDown,
  Trash2,
  RotateCw,
} from "lucide-react";

const RETENTION_LABELS: Record<number, string> = {
  7: "7 jours",
  30: "30 jours",
  90: "3 mois",
};

interface RetentionBarProps {
  retentionJours: number;
  onRetentionChange: (jours: number) => void;
  confirmDeleteAll: boolean;
  onDeleteAllClick: () => void;
  deleting: boolean;
  onCancelDelete: () => void;
  hasItems: boolean;
}

export default function RetentionBar({
  retentionJours,
  onRetentionChange,
  confirmDeleteAll,
  onDeleteAllClick,
  deleting,
  onCancelDelete,
  hasItems,
}: RetentionBarProps) {
  const [open, setOpen] = useState(false);

  if (!hasItems) return null;

  return (
    <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
      {/* Retention selector */}
      <div className="relative">
        <button
          onClick={() => setOpen(!open)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-card border border-card-border text-sm text-muted hover:text-accent hover:border-accent/30 transition-all"
        >
          <ShieldCheck className="w-4 h-4" />
          Conservation : {RETENTION_LABELS[retentionJours] || `${retentionJours} jours`}
          <ChevronDown className={`w-3.5 h-3.5 transition-transform ${open ? "rotate-180" : ""}`} />
        </button>
        {open && (
          <div className="absolute top-full mt-1 left-0 bg-card border border-card-border rounded-xl shadow-xl p-1.5 z-20 min-w-[200px]">
            <p className="text-xs text-muted px-3 py-2 pb-1">Durée de conservation</p>
            {[7, 30, 90].map((j) => (
              <button
                key={j}
                onClick={() => {
                  onRetentionChange(j);
                  setOpen(false);
                }}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-all ${
                  retentionJours === j
                    ? "bg-accent/10 text-accent font-medium"
                    : "text-muted hover:text-foreground hover:bg-surface"
                }`}
              >
                <span className="font-medium">{RETENTION_LABELS[j]}</span>
                <span className="text-xs text-muted ml-2">
                  {j === 7 ? "Suppression rapide" : j === 90 ? "Conservation longue" : "Standard"}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Delete all */}
      <div className="flex items-center gap-2">
        {confirmDeleteAll && (
          <span className="text-xs text-red-400 font-medium">Confirmer ?</span>
        )}
        <button
          onClick={onDeleteAllClick}
          disabled={deleting}
          className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            confirmDeleteAll
              ? "bg-red-500/15 text-red-400 border border-red-500/30 hover:bg-red-500/25"
              : "bg-card border border-card-border text-muted hover:text-red-400 hover:border-red-500/20"
          }`}
        >
          {deleting ? (
            <RotateCw className="w-4 h-4 animate-spin" />
          ) : (
            <Trash2 className="w-4 h-4" />
          )}
          {confirmDeleteAll ? "Tout supprimer" : "Vider l'historique"}
        </button>
        {confirmDeleteAll && (
          <button
            onClick={onCancelDelete}
            className="px-3 py-2 text-sm text-muted hover:text-foreground transition-colors"
          >
            Annuler
          </button>
        )}
      </div>
    </div>
  );
}
