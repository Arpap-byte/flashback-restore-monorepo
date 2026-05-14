import { Metadata } from "next";
import Link from "next/link";
import { Building2, Mail, Shield, RefreshCw, CreditCard, Sparkles } from "lucide-react";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "APEX Cyber — Restauration de photos par IA",
  description: "APEX Cyber développe et exploite Flashback Restore, un service de restauration et d'animation de photos anciennes par intelligence artificielle.",
  robots: "noindex, nofollow",
};

export default function BusinessPage() {
  return (
    <div className="flex flex-col min-h-screen bg-background">
      {/* Header minimal */}
      <header className="border-b border-card-border bg-card/50 backdrop-blur">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-accent to-violet-600 flex items-center justify-center">
              <Sparkles className="w-4.5 h-4.5 text-white" />
            </div>
            <span className="text-lg font-bold tracking-tight">
              APEX <span className="text-accent">Cyber</span>
            </span>
          </Link>
        </div>
      </header>

      <main className="flex-1 max-w-4xl mx-auto px-6 py-16 space-y-16">
        {/* ── Hero / About ── */}
        <section>
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-accent/10 border border-accent/20 text-accent text-sm font-medium mb-6">
            <Building2 className="w-4 h-4" />
            À propos
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-foreground mb-6 font-[family-name:var(--font-playfair)]">
            APEX <span className="text-accent">Cyber</span>
          </h1>
          <p className="text-muted leading-relaxed text-lg mb-4">
            APEX Cyber est une entreprise française spécialisée dans le développement
            de solutions logicielles fondées sur l&apos;intelligence artificielle.
          </p>
          <p className="text-muted leading-relaxed">
            Notre produit principal,{" "}
            <strong className="text-foreground">Flashback Restore</strong>, permet
            aux utilisateurs de restaurer, coloriser et animer leurs photos
            anciennes grâce à des algorithmes d&apos;IA de pointe. Le service est
            accessible sur{" "}
            <a href="https://flashback-restore.com" className="text-accent hover:underline">
              flashback-restore.com
            </a>.
          </p>
        </section>

        {/* ── Products & Services ── */}
        <section>
          <h2 className="text-2xl font-bold text-foreground mb-6">Produits et services</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            {[
              {
                icon: Sparkles,
                title: "Restauration de photos par IA",
                desc: "Notre IA analyse et répare automatiquement les défauts des photos anciennes : rayures, taches, décoloration, pliures. Le résultat est disponible en quelques secondes.",
              },
              {
                icon: RefreshCw,
                title: "Colorisation automatique",
                desc: "Redonnez des couleurs naturelles à vos photos en noir et blanc grâce à notre technologie de colorisation par IA, fidèle à l'époque d'origine.",
              },
              {
                icon: Shield,
                title: "Animation de portraits",
                desc: "Donnez vie à vos portraits avec des animations faciales réalistes. L'IA génère une courte vidéo à partir d'une simple photo.",
              },
              {
                icon: CreditCard,
                title: "Abonnements et crédits",
                desc: "Plusieurs formules d'abonnement (Gratuit, Découverte, Premium, Annuel, Pro) avec des crédits mensuels pour utiliser nos services de restauration, colorisation et animation.",
              },
            ].map((item, i) => (
              <div key={i} className="bg-card border border-card-border rounded-2xl p-6 hover:border-accent/30 transition-colors">
                <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center mb-4">
                  <item.icon className="w-5 h-5 text-accent" />
                </div>
                <h3 className="text-foreground font-semibold mb-2">{item.title}</h3>
                <p className="text-muted text-sm leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ── Refund & Cancellation Policy ── */}
        <section>
          <h2 className="text-2xl font-bold text-foreground mb-6">Politique de remboursement et d&apos;annulation</h2>

          <div className="space-y-6">
            <div className="bg-card border border-card-border rounded-2xl p-6">
              <h3 className="text-foreground font-semibold mb-3 flex items-center gap-2">
                <RefreshCw className="w-5 h-5 text-accent" />
                Remboursements
              </h3>
              <p className="text-muted text-sm leading-relaxed mb-3">
                Flashback Restore fournit des services numériques de traitement
                d&apos;images par intelligence artificielle. En raison de la nature
                numérique et immédiate de nos services, les crédits consommés pour
                une restauration, colorisation ou animation réussie ne sont pas
                remboursables.
              </p>
              <p className="text-muted text-sm leading-relaxed">
                Cependant, si un traitement échoue pour des raisons techniques
                indépendantes de votre volonté (indisponibilité du service, erreur
                serveur), le crédit correspondant est automatiquement recrédité sur
                votre compte.
              </p>
            </div>

            <div className="bg-card border border-card-border rounded-2xl p-6">
              <h3 className="text-foreground font-semibold mb-3 flex items-center gap-2">
                <Shield className="w-5 h-5 text-accent" />
                Annulation d&apos;abonnement
              </h3>
              <p className="text-muted text-sm leading-relaxed mb-3">
                Vous pouvez annuler votre abonnement à tout moment, sans engagement
                et sans frais, directement depuis votre espace client (Dashboard)
                ou en nous contactant. L&apos;annulation prend effet à la fin de la
                période de facturation en cours. Vous conservez l&apos;accès à
                votre abonnement jusqu&apos;à cette date.
              </p>
              <p className="text-muted text-sm leading-relaxed">
                Les abonnements sont gérés via Stripe, notre partenaire de paiement
                sécurisé. Aucune donnée bancaire n&apos;est stockée sur nos serveurs.
              </p>
            </div>

            <div className="bg-card border border-card-border rounded-2xl p-6">
              <h3 className="text-foreground font-semibold mb-3 flex items-center gap-2">
                <CreditCard className="w-5 h-5 text-accent" />
                Litiges et contestations
              </h3>
              <p className="text-muted text-sm leading-relaxed">
                En cas de litige concernant un paiement, nous vous invitons à nous
                contacter en priorité afin de résoudre le problème à l&apos;amiable.
                Nous répondons à toutes les demandes sous 48 heures ouvrées. Si
                aucune solution n&apos;est trouvée, vous conservez le droit
                d&apos;initier une procédure de contestation via votre établissement
                bancaire ou Stripe.
              </p>
            </div>
          </div>
        </section>

        {/* ── Contact ── */}
        <section>
          <h2 className="text-2xl font-bold text-foreground mb-6">Contact</h2>
          <div className="bg-card border border-card-border rounded-2xl p-6">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center flex-shrink-0">
                <Mail className="w-5 h-5 text-accent" />
              </div>
              <div>
                <h3 className="text-foreground font-semibold mb-2">Service client</h3>
                <p className="text-muted text-sm leading-relaxed mb-3">
                  Notre équipe est disponible pour toute question concernant nos
                  services, votre compte, la facturation ou l&apos;assistance
                  technique.
                </p>
                <div className="space-y-1.5 text-sm">
                  <p className="text-foreground">
                    Email :{" "}
                    <a href="mailto:apexcyber.eu@gmail.com" className="text-accent hover:underline">
                      apexcyber.eu@gmail.com
                    </a>
                  </p>
                  <p className="text-muted text-xs">
                    Délai de réponse : 24 à 48 heures ouvrées.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── Legal ── */}
        <section>
          <h2 className="text-2xl font-bold text-foreground mb-6">Informations légales</h2>
          <div className="bg-card border border-card-border rounded-2xl p-6">
            <div className="grid sm:grid-cols-2 gap-4 text-sm">
              <div>
                <h3 className="text-foreground font-semibold mb-1">Raison sociale</h3>
                <p className="text-muted">APEX Cyber</p>
              </div>
              <div>
                <h3 className="text-foreground font-semibold mb-1">Produit</h3>
                <p className="text-muted">Flashback Restore</p>
              </div>
              <div>
                <h3 className="text-foreground font-semibold mb-1">Site web</h3>
                <p className="text-muted">
                  <a href="https://flashback-restore.com" className="text-accent hover:underline">
                    flashback-restore.com
                  </a>
                </p>
              </div>
              <div>
                <h3 className="text-foreground font-semibold mb-1">Pays</h3>
                <p className="text-muted">France</p>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap gap-4 mt-6">
            <Link href="/privacy" className="text-sm text-muted hover:text-accent transition-colors">
              Politique de confidentialité
            </Link>
            <Link href="/terms" className="text-sm text-muted hover:text-accent transition-colors">
              Conditions d&apos;utilisation
            </Link>
            <Link href="/cookies" className="text-sm text-muted hover:text-accent transition-colors">
              Politique de cookies
            </Link>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
