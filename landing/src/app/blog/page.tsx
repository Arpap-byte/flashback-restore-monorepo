import { Metadata } from "next";
import Link from "next/link";
import { blogPosts } from "@/lib/blog-posts";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Sparkles, Clock, Calendar, ArrowRight, BookOpen } from "lucide-react";

export const metadata: Metadata = {
  title: "Blog Flashback Restore — Conseils et guides restauration photo IA",
  description:
    "Découvrez nos guides et comparatifs sur la restauration de photos anciennes par intelligence artificielle. Tutoriels, astuces et comparatifs d'outils.",
  keywords: [
    "blog restauration photo",
    "guide restauration photo IA",
    "tutoriel photo ancienne",
    "comparatif outil restauration photo",
    "conseils restauration photo",
  ],
  openGraph: {
    title: "Blog Flashback Restore — Conseils et guides restauration photo IA",
    description:
      "Découvrez nos guides et comparatifs sur la restauration de photos anciennes par intelligence artificielle.",
    type: "website",
    locale: "fr_FR",
    siteName: "Flashback Restore",
  },
  alternates: {
    canonical: "https://flashback-restore.com/blog",
  },
};

export default function BlogPage() {
  return (
    <div className="flex flex-col min-h-screen bg-background">
      <Navbar />
      <main className="flex-1 pt-28 pb-16">
        {/* Background glows */}
        <div className="fixed inset-0 pointer-events-none">
          <div className="absolute top-1/3 left-1/4 w-[700px] h-[700px] bg-violet-600/5 rounded-full blur-[130px]" />
          <div className="absolute bottom-1/3 right-1/4 w-[600px] h-[600px] bg-accent/4 rounded-full blur-[110px]" />
        </div>

        <div className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Hero */}
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-accent/10 border border-accent/20 text-accent text-sm font-medium mb-6">
              <BookOpen className="w-4 h-4" />
              Blog
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-4 font-[family-name:var(--font-playfair)]">
              Le blog{" "}
              <span className="text-gradient">Flashback Restore</span>
            </h1>
            <p className="text-muted text-lg max-w-2xl mx-auto">
              Guides, tutoriels et comparatifs pour vous aider à restaurer et
              préserver vos photos anciennes grâce à l&apos;intelligence
              artificielle.
            </p>
          </div>

          {/* Breadcrumb */}
          <div className="flex items-center gap-2 text-sm text-muted mb-10">
            <Link href="/" className="hover:text-accent transition-colors">
              Accueil
            </Link>
            <span className="text-muted/40">/</span>
            <span className="text-foreground">Blog</span>
          </div>

          {/* Blog posts grid */}
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {blogPosts.map((post) => (
              <Link
                key={post.slug}
                href={`/blog/${post.slug}`}
                className="group bg-card border border-card-border rounded-2xl overflow-hidden hover:border-muted/50 hover:shadow-xl hover:shadow-accent/5 transition-all duration-300"
              >
                {/* Image placeholder with gradient */}
                <div className="relative h-48 bg-gradient-to-br from-accent/20 via-violet-500/10 to-surface-alt overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-br from-accent/10 to-transparent opacity-50 group-hover:opacity-70 transition-opacity" />
                  <div className="absolute top-4 left-4">
                    <span className="text-xs bg-accent/20 text-accent px-3 py-1 rounded-full font-medium border border-accent/20">
                      {post.category}
                    </span>
                  </div>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <Sparkles className="w-12 h-12 text-accent/30 group-hover:text-accent/50 group-hover:scale-110 transition-all" />
                  </div>
                </div>

                <div className="p-6">
                  <div className="flex items-center gap-4 text-xs text-muted mb-3">
                    <span className="flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5" />
                      {new Date(post.date).toLocaleDateString("fr-FR", {
                        year: "numeric",
                        month: "long",
                        day: "numeric",
                      })}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5" />
                      {post.readTime} de lecture
                    </span>
                  </div>

                  <h2 className="text-lg font-bold text-foreground mb-2 group-hover:text-accent transition-colors line-clamp-2 font-[family-name:var(--font-playfair)]">
                    {post.title}
                  </h2>
                  <p className="text-muted text-sm leading-relaxed line-clamp-3 mb-4">
                    {post.description}
                  </p>

                  <div className="flex items-center gap-1.5 text-accent text-sm font-medium">
                    Lire l&apos;article
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </div>
                </div>
              </Link>
            ))}
          </div>

          {/* Newsletter / CTA */}
          <div className="mt-20 text-center p-8 sm:p-12 rounded-3xl bg-gradient-to-br from-accent/10 via-violet-500/5 to-transparent border border-card-border">
            <Sparkles className="w-10 h-10 text-accent mx-auto mb-4" />
            <h2 className="text-2xl sm:text-3xl font-bold text-foreground mb-3 font-[family-name:var(--font-playfair)]">
              Prêt à restaurer vos souvenirs ?
            </h2>
            <p className="text-muted mb-6 max-w-md mx-auto">
              Essayez Flashback Restore gratuitement. Importez une photo
              ancienne et découvrez la magie de l&apos;IA en quelques secondes.
            </p>
            <Link
              href="/restore"
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-full bg-accent text-white dark:text-gray-950 font-semibold text-base hover:brightness-110 transition-all hover:shadow-xl hover:shadow-accent/30 active:scale-95"
            >
              <Sparkles className="w-5 h-5" />
              Restaurer une photo gratuitement
            </Link>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
