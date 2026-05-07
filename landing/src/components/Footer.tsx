"use client";

import { Sparkles, Heart } from "lucide-react";
import Link from "next/link";
import { FaTwitter, FaInstagram, FaTiktok } from "react-icons/fa";

const footerLinks = {
  Produit: [
    { label: "Fonctionnalités", href: "/#features" },
    { label: "Comment ça marche", href: "/#how-it-works" },
    { label: "Tarifs", href: "/#pricing" },
    { label: "FAQ", href: "/#faq" },
    { label: "Restaurer une photo", href: "/upload" },
  ],
  Entreprise: [
    { label: "À propos", href: "/about" },
    { label: "Restaurer", href: "/upload" },
    { label: "Animer", href: "/animate" },
    { label: "Nous contacter", href: "mailto:support@flashback-restore.com" },
  ],
  Légal: [
    { label: "Confidentialité", href: "/privacy" },
    { label: "Conditions d'utilisation", href: "/terms" },
    { label: "Cookies", href: "/cookies" },
    { label: "Mentions légales", href: "/terms" },
  ],
};

export default function Footer() {
  return (
    <footer className="relative bg-card border-t border-card-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-10">
          {/* Brand */}
          <div className="lg:col-span-2">
            <Link href="/" className="flex items-center gap-2.5 group mb-4">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent to-violet-600 flex items-center justify-center group-hover:scale-105 transition-transform shadow-lg shadow-accent/25">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <span className="text-lg font-bold text-foreground tracking-tight">
                Flashback{" "}
                <span className="text-accent">Restore</span>
              </span>
            </Link>
            <p className="text-muted text-sm leading-relaxed max-w-xs mb-6">
              Redonnez vie à vos souvenirs grâce à l&apos;intelligence
              artificielle. Restaurez et animez vos photos anciennes en quelques
              secondes.
            </p>
            {/* Social */}
            <div className="flex items-center gap-2.5">
              {[
                { icon: FaTwitter, label: "Twitter" },
                { icon: FaInstagram, label: "Instagram" },
                { icon: FaTiktok, label: "TikTok" },
              ].map(({ icon: Icon, label }) => (
                <Link
                  key={label}
                  href="#"
                  className="w-9 h-9 rounded-lg bg-surface border border-card-border flex items-center justify-center text-muted hover:text-accent hover:border-accent/30 hover:bg-accent/5 transition-all"
                  aria-label={label}
                >
                  <Icon className="w-4 h-4" />
                </Link>
              ))}
            </div>
          </div>

          {/* Links */}
          {Object.entries(footerLinks).map(([category, links]) => (
            <div key={category}>
              <h4 className="text-foreground font-semibold text-sm mb-4">
                {category}
              </h4>
              <ul className="space-y-3">
                {links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-muted hover:text-accent text-sm transition-colors"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom */}
        <div className="mt-12 pt-8 border-t border-card-border flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-muted/60 text-sm">
            © {new Date().getFullYear()} Flashback Restore. Tous droits
            réservés.
          </p>
          <p className="text-muted/60 text-sm inline-flex items-center gap-1.5">
            Fait avec{" "}
            <Heart className="w-3.5 h-3.5 fill-red-500 text-red-500" />{" "}
            en France
          </p>
        </div>
      </div>
    </footer>
  );
}
