"use client";

import { Sparkles } from "lucide-react";
import { FaTwitter, FaInstagram, FaTiktok } from "react-icons/fa";

const footerLinks = {
  Produit: [
    { label: "Fonctionnalités", href: "#features" },
    { label: "Tarifs", href: "#pricing" },
    { label: "FAQ", href: "#faq" },
    { label: "Télécharger", href: "#cta" },
  ],
  Entreprise: [
    { label: "À propos", href: "#" },
    { label: "Blog", href: "#" },
    { label: "Carrières", href: "#" },
    { label: "Presse", href: "#" },
  ],
  Légal: [
    { label: "Confidentialité", href: "#" },
    { label: "Conditions d'utilisation", href: "#" },
    { label: "Cookies", href: "#" },
    { label: "Mentions légales", href: "#" },
  ],
};

export default function Footer() {
  return (
    <footer className="relative bg-gray-950 border-t border-white/5">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-10">
          {/* Brand */}
          <div className="lg:col-span-2">
            <a href="#" className="flex items-center gap-2 group mb-4">
              <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-amber-400 to-violet-600 flex items-center justify-center group-hover:scale-105 transition-transform">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <span className="text-lg font-bold text-white tracking-tight">
                Flashback{" "}
                <span className="text-amber-400">Restore</span>
              </span>
            </a>
            <p className="text-gray-500 text-sm leading-relaxed max-w-xs mb-6">
              Redonnez vie à vos souvenirs grâce à l&apos;intelligence
              artificielle. Restaurez et animez vos photos anciennes en quelques
              secondes.
            </p>
            {/* Social */}
            <div className="flex items-center gap-3">
              <a
                href="#"
                className="w-9 h-9 rounded-lg bg-white/5 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
                aria-label="Twitter"
              >
                <FaTwitter className="w-4 h-4" />
              </a>
              <a
                href="#"
                className="w-9 h-9 rounded-lg bg-white/5 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
                aria-label="Instagram"
              >
                <FaInstagram className="w-4 h-4" />
              </a>
              <a
                href="#"
                className="w-9 h-9 rounded-lg bg-white/5 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
                aria-label="TikTok"
              >
                <FaTiktok className="w-4 h-4" />
              </a>
            </div>
          </div>

          {/* Links */}
          {Object.entries(footerLinks).map(([category, links]) => (
            <div key={category}>
              <h4 className="text-white font-semibold text-sm mb-4">
                {category}
              </h4>
              <ul className="space-y-3">
                {links.map((link) => (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      className="text-gray-500 hover:text-amber-400 text-sm transition-colors"
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom */}
        <div className="mt-12 pt-8 border-t border-white/5 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-gray-600 text-sm">
            © {new Date().getFullYear()} Flashback Restore. Tous droits
            réservés.
          </p>
          <p className="text-gray-600 text-sm">
            Made with ❤️ en France
          </p>
        </div>
      </div>
    </footer>
  );
}
