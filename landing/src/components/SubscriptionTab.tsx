"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  CreditCard,
  Receipt,
  ExternalLink,
  RefreshCw,
  Loader2,
  AlertTriangle,
  FileText,
  Calendar,
  Download,
  ShieldCheck,
} from "lucide-react";
import { getSubscription, openStripePortal, SubscriptionInfo } from "@/lib/api";

export default function SubscriptionTab() {
  const [sub, setSub] = useState<SubscriptionInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [portalLoading, setPortalLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSubscription()
      .then(setSub)
      .catch((err) => setError(err instanceof Error ? err.message : "Erreur"))
      .finally(() => setLoading(false));
  }, []);

  const handlePortal = async () => {
    setPortalLoading(true);
    try {
      const { url } = await openStripePortal();
      window.location.href = url;
    } catch {
      setError("Impossible d'ouvrir le portail client.");
    } finally {
      setPortalLoading(false);
    }
  };

  const formatDate = (iso: string | null) => {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("fr-FR", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  };

  const statutLabel = (statut: string) => {
    const map: Record<string, string> = {
      active: "Actif",
      past_due: "En retard",
      canceled: "Résilié",
      incomplete: "En attente",
      unpaid: "Impayé",
      trialing: "Essai",
      indisponible: "Indisponible",
    };
    return map[statut] || statut;
  };

  const statutColor = (statut: string) => {
    if (statut === "active" || statut === "trialing") return "text-green-400";
    if (statut === "past_due" || statut === "unpaid") return "text-red-400";
    if (statut === "canceled") return "text-amber-400";
    return "text-muted";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-accent" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 justify-center py-10 text-red-400">
        <AlertTriangle className="w-4 h-4" />
        {error}
      </div>
    );
  }

  if (!sub) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      {/* ── Résumé abonnement ── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Plan */}
        <div className="bg-card border border-card-border rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <CreditCard className="w-4 h-4 text-accent" />
            <span className="text-xs font-semibold text-muted uppercase tracking-wider">
              Abonnement
            </span>
          </div>
          <p className="text-xl font-bold text-foreground capitalize mb-1">
            {sub.plan}
          </p>
          {sub.stripe && (
            <p className={`text-sm ${statutColor(sub.stripe.statut)}`}>
              {statutLabel(sub.stripe.statut)}
              {sub.stripe.annulation_auto && " (résiliation programmée)"}
            </p>
          )}
        </div>

        {/* Crédits */}
        <div className="bg-card border border-card-border rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <RefreshCw className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-semibold text-muted uppercase tracking-wider">
              Crédits
            </span>
          </div>
          <p className="text-xl font-bold text-foreground">
            {sub.credits}
          </p>
          <p className="text-xs text-muted">
            + {sub.essais_restants} essais gratuits restants
          </p>
        </div>

        {/* Renouvellement */}
        <div className="bg-card border border-card-border rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Calendar className="w-4 h-4 text-violet-400" />
            <span className="text-xs font-semibold text-muted uppercase tracking-wider">
              Renouvellement
            </span>
          </div>
          <p className="text-xl font-bold text-foreground">
            {formatDate(sub.date_renouvellement)}
          </p>
          {sub.stripe?.fin_periode && (
            <p className="text-xs text-muted">
              Période Stripe : {formatDate(sub.stripe.fin_periode)}
            </p>
          )}
        </div>
      </div>

      {/* ── Actions ── */}
      <div className="flex flex-wrap gap-3">
        {sub.est_abonne && (
          <button
            onClick={handlePortal}
            disabled={portalLoading}
            className="inline-flex items-center gap-2 px-5 py-3 rounded-full bg-accent text-white text-sm font-semibold hover:brightness-110 transition-all active:scale-[0.97] shadow-md shadow-accent/20"
          >
            {portalLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <ExternalLink className="w-4 h-4" />
            )}
            Portail client Stripe
          </button>
        )}
      </div>

      {/* ── Factures ── */}
      {sub.factures.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
            <Receipt className="w-4 h-4 text-accent" />
            Dernières factures
          </h3>
          <div className="space-y-2">
            {sub.factures.map((inv) => (
              <motion.div
                key={inv.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl bg-surface border border-card-border hover:border-card-border/70 transition-all"
              >
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-lg bg-accent/10 flex items-center justify-center flex-shrink-0">
                    <FileText className="w-4 h-4 text-accent" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-foreground">
                      Facture {inv.number || inv.id.slice(-8)}
                    </p>
                    <p className="text-xs text-muted">
                      {formatDate(inv.date)}
                      {inv.periode_debut && inv.periode_fin && (
                        <> — du {formatDate(inv.periode_debut)} au {formatDate(inv.periode_fin)}</>
                      )}
                    </p>
                    <p className="text-xs text-muted mt-0.5">
                      <span
                        className={
                          inv.statut === "paid"
                            ? "text-green-400"
                            : "text-amber-400"
                        }
                      >
                        {statutLabel(inv.statut)}
                      </span>
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-sm font-semibold text-foreground whitespace-nowrap">
                    {inv.montant.toFixed(2)} {inv.devise}
                  </span>

                  {inv.url_pdf && (
                    <a
                      href={inv.url_pdf}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-2 rounded-full border border-card-border text-muted hover:text-foreground hover:border-accent/30 transition-all text-xs"
                    >
                      <Download className="w-3 h-3" />
                      PDF
                    </a>
                  )}

                  {inv.url_portail && (
                    <a
                      href={inv.url_portail}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-2 rounded-full border border-card-border text-muted hover:text-foreground hover:border-accent/30 transition-all text-xs"
                    >
                      <ExternalLink className="w-3 h-3" />
                      Voir
                    </a>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* ── Garantie ── */}
      <div className="flex items-center gap-2 text-xs text-muted pt-2">
        <ShieldCheck className="w-3.5 h-3.5 text-accent/60" />
        Paiement sécurisé via Stripe. Vos données bancaires ne sont jamais
        stockées sur nos serveurs.
      </div>
    </motion.div>
  );
}
