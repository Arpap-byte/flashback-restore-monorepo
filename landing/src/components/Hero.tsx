"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowRight, Play, Sparkles, Star, Shield, Zap } from "lucide-react";
import { useTheme } from "@/components/ThemeProvider";

function FloatingParticles() {
  const particles = Array.from({ length: 25 }, (_, i) => ({
    id: i,
    size: Math.random() * 5 + 2,
    left: Math.random() * 100,
    delay: Math.random() * 10,
    duration: Math.random() * 8 + 6,
    opacity: Math.random() * 0.25 + 0.04,
  }));

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((p) => (
        <div
          key={p.id}
          className="absolute rounded-full bg-accent/30 dark:bg-amber-400/25 animate-float"
          style={{
            width: p.size,
            height: p.size,
            left: `${p.left}%`,
            bottom: `${Math.random() * 100}%`,
            animationDelay: `${p.delay}s`,
            animationDuration: `${p.duration}s`,
            opacity: p.opacity,
          }}
        />
      ))}
    </div>
  );
}

function BeforeAfterDemo() {
  const { theme } = useTheme();
  const isDark = theme === "dark";

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.8, delay: 0.6 }}
      className="relative mx-auto max-w-md mt-12 lg:mt-16"
    >
      {/* Main card */}
      <div className="relative rounded-2xl overflow-hidden border border-card-border shadow-2xl shadow-black/20 bg-card">
        {/* Split before/after */}
        <div className="relative aspect-[4/3] overflow-hidden bg-surface-alt">
          {/* Before side */}
          <div className="absolute inset-y-0 left-0 w-1/2 overflow-hidden">
            <img
              src="/demo/before.jpg"
              alt="Photo avant restauration"
              className="w-full h-full object-cover"
            />
            {/* Sepia overlay for aged effect */}
            <div className="absolute inset-0 bg-gradient-to-r from-amber-900/30 to-transparent pointer-events-none" />
            {/* Label */}
            <div className="absolute top-3 left-3">
              <span className="inline-block text-xs font-semibold uppercase tracking-wider text-white/90 bg-black/50 backdrop-blur-sm px-3 py-1 rounded-full border border-white/10">
                Avant
              </span>
            </div>
          </div>

          {/* Divider */}
          <div className="absolute inset-y-0 left-1/2 w-[2px] bg-gradient-to-b from-accent via-accent to-transparent z-10" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-accent text-white dark:text-gray-950 flex items-center justify-center z-20 shadow-lg shadow-accent/40">
            <span className="text-xs font-bold">VS</span>
          </div>

          {/* After side */}
          <div className="absolute inset-y-0 right-0 w-1/2 overflow-hidden">
            <img
              src="/demo/after.jpg"
              alt="Photo après restauration"
              className="w-full h-full object-cover"
            />
            {/* Brightness overlay for restored effect */}
            <div className="absolute inset-0 bg-gradient-to-t from-accent/10 to-transparent pointer-events-none" />
            {/* Label */}
            <div className="absolute top-3 right-3">
              <span className="inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-wider bg-accent/90 text-white dark:text-gray-950 px-3 py-1 rounded-full border border-accent shadow-lg shadow-accent/20">
                <Sparkles className="w-3 h-3" />
                Après
              </span>
            </div>
            {/* Subtle glow pulse on restored side */}
            <motion.div
              className="absolute inset-0 bg-gradient-to-t from-accent/15 to-transparent pointer-events-none"
              animate={{ opacity: [0.3, 0.6, 0.3] }}
              transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            />
          </div>
        </div>

        {/* Bottom info bar */}
        <div className="px-4 py-3 border-t border-card-border flex items-center justify-between text-xs text-muted bg-card">
          <span className="flex items-center gap-1">
            <Zap className="w-3 h-3 text-accent" />
            Restauration en 5 secondes
          </span>
          <span className="flex items-center gap-1">
            <Shield className="w-3 h-3 text-emerald-500" />
            Qualité HD
          </span>
        </div>
      </div>

      {/* Background glow */}
      <div className="absolute -inset-4 bg-gradient-to-br from-accent/20 via-violet-500/10 to-transparent rounded-3xl blur-3xl -z-10 opacity-40" />
    </motion.div>
  );
}

export default function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Background gradients */}
      <div className="absolute inset-0 bg-background">
        <div className="absolute top-[15%] left-[10%] w-[500px] h-[500px] bg-violet-600/8 rounded-full blur-[120px]" />
        <div className="absolute bottom-[20%] right-[10%] w-[400px] h-[400px] bg-accent/8 rounded-full blur-[100px]" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] bg-gradient-to-br from-accent/8 via-violet-600/6 to-transparent rounded-full blur-[150px]" />
      </div>

      <FloatingParticles />

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 py-32 lg:py-40">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          {/* Left: Text content */}
          <div className="text-center lg:text-left">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.2 }}
            >
              {/* Badge */}
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-accent/10 border border-accent/20 text-accent text-sm font-medium mb-8">
                <Sparkles className="w-4 h-4" />
                Propulsé par l&apos;intelligence artificielle
              </div>
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.35 }}
              className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight text-foreground leading-[1.08] mb-6"
            >
              Redonnez vie à
              <br />
              <span className="text-gradient">vos souvenirs</span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.5 }}
              className="text-lg sm:text-xl text-muted max-w-xl lg:max-w-none mx-auto lg:mx-0 mb-10 leading-relaxed"
            >
              Restaurez et animez vos photos anciennes grâce à
              l&apos;intelligence artificielle. Comme par magie, vos souvenirs
              prennent vie — restauration des couleurs, réparation des défauts,
              et animation façon portrait vivant.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.65 }}
              className="flex flex-col sm:flex-row items-center gap-4 justify-center lg:justify-start"
            >
              <Link
                href="/upload"
                className="group inline-flex items-center gap-2 px-8 py-4 rounded-full bg-accent text-white dark:text-gray-950 font-semibold text-base hover:brightness-110 transition-all hover:shadow-xl hover:shadow-accent/30 active:scale-[0.97] w-full sm:w-auto justify-center"
              >
                Commencer gratuitement
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link
                href="/#how-it-works"
                className="group inline-flex items-center gap-2 px-8 py-4 rounded-full border border-card-border text-foreground font-semibold text-base hover:bg-card transition-all hover:border-accent/30 active:scale-[0.97] w-full sm:w-auto justify-center"
              >
                <Play className="w-5 h-5 text-accent" />
                Comment ça marche
              </Link>
            </motion.div>

            {/* Stats */}
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.8 }}
              className="mt-12 flex items-center gap-8 justify-center lg:justify-start"
            >
              {[
                { value: "50K+", label: "Photos restaurées" },
                { value: "4.8", label: "Note App Store", icon: Star },
                { value: "10K+", label: "Utilisateurs" },
              ].map((stat) => (
                <div key={stat.label} className="text-center">
                  <div className="text-2xl sm:text-3xl font-bold text-foreground flex items-center justify-center gap-1">
                    {stat.value}
                    {stat.icon && (
                      <stat.icon className="w-4 h-4 fill-accent text-accent" />
                    )}
                  </div>
                  <div className="text-xs sm:text-sm text-muted mt-1">
                    {stat.label}
                  </div>
                </div>
              ))}
            </motion.div>
          </div>

          {/* Right: Before/After Demo */}
          <div className="hidden lg:block">
            <BeforeAfterDemo />
          </div>

          {/* Mobile: smaller demo */}
          <div className="lg:hidden">
            <BeforeAfterDemo />
          </div>
        </div>
      </div>

      {/* Bottom fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-background to-transparent pointer-events-none" />
    </section>
  );
}
