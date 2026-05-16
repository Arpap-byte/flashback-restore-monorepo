"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X, Sparkles, Sun, Moon, User, History, LayoutDashboard } from "lucide-react";
import { useTheme } from "@/components/ThemeProvider";
import { UserButton, SignInButton, useAuth, useClerk } from "@clerk/nextjs";
import { LogOut } from "lucide-react";

const navLinks = [
  { label: "Accueil", href: "/" },
  { label: "Restaurer", href: "/restore" },
  { label: "Animer", href: "/animate" },
  { label: "Tarifs", href: "/#pricing" },
  { label: "Blog", href: "/blog" },
];

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const { isSignedIn } = useAuth();
  const { signOut } = useClerk();
  const pathname = usePathname();

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 40);
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <motion.header
      initial={{ y: -100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-background/80 backdrop-blur-xl border-b border-card-border shadow-lg shadow-black/10 dark:shadow-black/30"
          : "bg-transparent"
      }`}
    >
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 lg:h-20">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="relative w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-amber-600 dark:from-amber-400 dark:to-violet-600 flex items-center justify-center group-hover:scale-105 transition-transform shadow-lg shadow-amber-500/25">
              <Sparkles className="w-5 h-5 text-white" />
              <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-amber-400/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
            <span className="text-lg font-bold tracking-tight">
              <span className="text-foreground">Flashback</span>{" "}
              <span className="text-accent">Restore</span>
            </span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden lg:flex items-center gap-1">
            {navLinks.map((link) => {
              const isActive = pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href));
              return (
              <Link
                key={link.href}
                href={link.href}
                className={`text-sm font-medium px-3 py-2 rounded-lg transition-colors ${
                  isActive
                    ? "text-accent bg-accent/5 font-semibold"
                    : "text-muted hover:text-accent hover:bg-accent/5"
                }`}
              >
                {link.label}
              </Link>
            )})}
          </div>

          {/* Right side */}
          <div className="hidden lg:flex items-center gap-3">
            {/* Theme toggle */}
            <button
              onClick={toggleTheme}
              className="w-9 h-9 rounded-lg bg-card border border-card-border flex items-center justify-center text-muted hover:text-accent hover:border-accent/30 transition-all"
              aria-label="Changer le thème"
            >
              {theme === "dark" ? (
                <Sun className="w-4 h-4" />
              ) : (
                <Moon className="w-4 h-4" />
              )}
            </button>

            {isSignedIn ? (
              <>
                <Link
                  href="/historique"
                  className="text-sm text-muted hover:text-accent transition-colors font-medium px-3 py-2 rounded-lg hover:bg-accent/5 flex items-center gap-1.5"
                >
                  <History className="w-4 h-4" />
                  Historique
                </Link>
                <Link
                  href="/dashboard"
                  className="text-sm text-muted hover:text-accent transition-colors font-medium px-3 py-2 rounded-lg hover:bg-accent/5 flex items-center gap-1.5"
                >
                  <LayoutDashboard className="w-4 h-4" />
                  Dashboard
                </Link>
                <div className="flex items-center">
                  <UserButton
                    appearance={{
                      elements: {
                        userButtonBox: "flex items-center",
                        userButtonTrigger:
                          "rounded-full border border-card-border hover:border-accent/50 transition-all",
                        userButtonPopoverCard:
                          "bg-[#1c1917] border border-[#292524] shadow-2xl rounded-xl",
                        userButtonPopoverActionButton:
                          "text-muted hover:text-white hover:bg-[#292524] rounded-lg",
                        userButtonPopoverActionButtonText: "text-muted",
                        userButtonPopoverFooter: "hidden",
                      },
                    }}
                  />
                </div>
                <button
                  onClick={() => signOut()}
                  className="text-sm text-muted hover:text-red-400 transition-colors font-medium px-3 py-2 rounded-lg hover:bg-red-400/5 flex items-center gap-1.5"
                  title="Déconnexion"
                >
                  <LogOut className="w-4 h-4" />
                  Déconnexion
                </button>
              </>
            ) : (
              <SignInButton mode="modal">
                <button className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full border border-card-border text-foreground hover:bg-surface text-sm font-medium transition-all cursor-pointer">
                  <User className="w-4 h-4" />
                  Connexion
                </button>
              </SignInButton>
            )}

            {/* CTA */}
            <Link
              href="/restore"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-accent text-white dark:text-gray-950 text-sm font-semibold hover:brightness-110 transition-all hover:shadow-lg hover:shadow-accent/25 active:scale-95"
            >
              <Sparkles className="w-4 h-4" />
              Restaurer une photo
            </Link>
          </div>

          {/* Mobile menu button */}
          <div className="flex items-center gap-2 lg:hidden">
            <button
              onClick={toggleTheme}
              className="w-9 h-9 rounded-lg bg-card border border-card-border flex items-center justify-center text-muted"
              aria-label="Changer le thème"
            >
              {theme === "dark" ? (
                <Sun className="w-4 h-4" />
              ) : (
                <Moon className="w-4 h-4" />
              )}
            </button>
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="p-2 text-muted hover:text-foreground transition-colors"
              aria-label="Menu"
            >
              {mobileOpen ? (
                <X className="w-6 h-6" />
              ) : (
                <Menu className="w-6 h-6" />
              )}
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile menu */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
            className="lg:hidden bg-card/95 backdrop-blur-xl border-b border-card-border overflow-hidden"
          >
            <div className="px-4 py-4 space-y-1">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileOpen(false)}
                  className="block py-2.5 px-3 text-muted hover:text-accent hover:bg-accent/5 rounded-lg transition-colors font-medium"
                >
                  {link.label}
                </Link>
              ))}
              {isSignedIn ? (
                <>
                  <Link
                    href="/historique"
                    onClick={() => setMobileOpen(false)}
                    className="block py-2.5 px-3 text-muted hover:text-accent hover:bg-accent/5 rounded-lg transition-colors font-medium"
                  >
                    Historique
                  </Link>
                  <Link
                    href="/dashboard"
                    onClick={() => setMobileOpen(false)}
                    className="block py-2.5 px-3 text-muted hover:text-accent hover:bg-accent/5 rounded-lg transition-colors font-medium"
                  >
                    Dashboard
                  </Link>
                  <button
                    onClick={() => { signOut(); setMobileOpen(false); }}
                    className="block w-full text-left py-2.5 px-3 text-muted hover:text-red-400 hover:bg-red-400/5 rounded-lg transition-colors font-medium"
                  >
                    Déconnexion
                  </button>
                </>
              ) : (
                <SignInButton mode="modal">
                  <button className="block w-full text-left py-2.5 px-3 text-muted hover:text-accent hover:bg-accent/5 rounded-lg transition-colors font-medium cursor-pointer">
                    Connexion
                  </button>
                </SignInButton>
              )}
              <Link
                href="/restore"
                onClick={() => setMobileOpen(false)}
                className="mt-2 inline-flex items-center gap-2 px-5 py-3 rounded-full bg-accent text-white dark:text-gray-950 text-sm font-semibold hover:brightness-110 transition-all w-full justify-center"
              >
                <Sparkles className="w-4 h-4" />
                Restaurer une photo
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.header>
  );
}
