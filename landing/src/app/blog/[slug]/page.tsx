import { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getBlogPost, getAllSlugs } from "@/lib/blog-posts";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { ShareButtons } from "@/components/ShareButtons";
import {
  Sparkles,
  Clock,
  Calendar,
  Tag,
  ChevronRight,
  ArrowLeft,
} from "lucide-react";

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateStaticParams() {
  return getAllSlugs().map((slug) => ({ slug }));
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const post = getBlogPost(slug);

  if (!post) {
    return { title: "Article non trouvé" };
  }

  return {
    title: `${post.title} — Blog Flashback Restore`,
    description: post.description,
    keywords: post.keywords,
    openGraph: {
      title: post.title,
      description: post.description,
      type: "article",
      publishedTime: post.date,
      locale: "fr_FR",
      siteName: "Flashback Restore",
    },
    alternates: {
      canonical: `https://flashback-restore.com/blog/${post.slug}`,
    },
  };
}

export default async function BlogPostPage({ params }: PageProps) {
  const { slug } = await params;
  const post = getBlogPost(slug);

  if (!post) {
    notFound();
  }

  const shareUrl = `https://flashback-restore.com/blog/${post.slug}`;

  return (
    <div className="flex flex-col min-h-screen bg-background">
      <Navbar />
      <main className="flex-1 pt-28 pb-16">
        {/* Background glows */}
        <div className="fixed inset-0 pointer-events-none">
          <div className="absolute top-1/3 left-1/4 w-[700px] h-[700px] bg-violet-600/5 rounded-full blur-[130px]" />
          <div className="absolute bottom-1/3 right-1/4 w-[600px] h-[600px] bg-accent/4 rounded-full blur-[110px]" />
        </div>

        <article className="relative z-10 max-w-3xl mx-auto px-4 sm:px-6">
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 text-sm text-muted mb-8">
            <Link href="/" className="hover:text-accent transition-colors">
              Accueil
            </Link>
            <ChevronRight className="w-3.5 h-3.5" />
            <Link href="/blog" className="hover:text-accent transition-colors">
              Blog
            </Link>
            <ChevronRight className="w-3.5 h-3.5" />
            <span className="text-foreground truncate max-w-[200px] sm:max-w-xs">
              {post.title}
            </span>
          </div>

          {/* Article header */}
          <header className="mb-10">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent/10 border border-accent/20 text-accent text-xs font-medium mb-4">
              <Tag className="w-3.5 h-3.5" />
              {post.category}
            </div>
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-foreground mb-4 font-[family-name:var(--font-playfair)] leading-tight">
              {post.title}
            </h1>
            <p className="text-lg text-muted leading-relaxed mb-6">
              {post.description}
            </p>
            <div className="flex flex-wrap items-center gap-4 text-sm text-muted">
              <span className="flex items-center gap-1.5">
                <Calendar className="w-4 h-4" />
                {new Date(post.date).toLocaleDateString("fr-FR", {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}
              </span>
              <span className="flex items-center gap-1.5">
                <Clock className="w-4 h-4" />
                {post.readTime} de lecture
              </span>
            </div>
          </header>

          {/* Share buttons */}
          <ShareButtons url={shareUrl} title={post.title} />

          {/* Article content */}
          <div className="prose-custom mb-12">{post.content}</div>

          {/* Back to blog */}
          <div className="pt-8 border-t border-card-border">
            <Link
              href="/blog"
              className="inline-flex items-center gap-2 text-muted hover:text-accent transition-colors text-sm font-medium"
            >
              <ArrowLeft className="w-4 h-4" />
              Retour au blog
            </Link>
          </div>
        </article>
      </main>
      <Footer />
    </div>
  );
}
