const API_BASE = typeof window === "undefined"
  ? (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
  : (process.env.NEXT_PUBLIC_API_URL || ""); // client : chemin relatif → même domaine HTTPS

export interface AnalysisResult {
  rayures: boolean;
  decoloration: boolean;
  taches: boolean;
  dechirures: boolean;
  bruit: boolean;
  etat_global: string;
  age_estime: string;
  recommandations: string[];
}

export interface RestoreResult {
  message: string;
  analyse: AnalysisResult;
  parametres?: {
    luminosite: number;
    contraste: number;
    saturation: number;
    nettete: number;
    debruitage: number;
    correction_rouge: number;
    correction_vert: number;
    correction_bleu: number;
  };
  url_image: string;
}

export interface AnimateResult {
  message: string;
  job_id: string;
}

export interface AnimationStatus {
  status: "en_attente" | "en_cours" | "termine" | "erreur";
  progress?: number;
  result_url?: string;
  message?: string;
}

export interface CheckoutResult {
  checkout_url: string;
}

export interface TravailHistorique {
  id: string;
  type: string;
  statut: string;
  url_original: string | null;
  url_resultat: string | null;
  url_animation: string | null;
  taille_original: number | null;
  taille_resultat: number | null;
  message_erreur: string | null;
  cree_le: string;
  expire_le: string | null;
}

/** Get the JWT for authenticating API calls (supports Clerk + NextAuth) */
async function getAuthHeader(): Promise<Record<string, string>> {
  if (typeof window === "undefined") return {};

  // 1. Clerk token (primary — Google/Facebook/Email via Clerk)
  try {
    // @ts-ignore — Clerk injects a global Clerk object
    const clerk = (window as any).Clerk;
    if (clerk?.session) {
      const token = await clerk.session.getToken();
      if (token) {
        return { Authorization: `Bearer ${token}` };
      }
    }
  } catch {}

  // 2. Fallback: localStorage token (legacy email/password auth)
  try {
    const stored = localStorage.getItem("flashback_auth");
    if (stored) {
      return { Authorization: `Bearer ${JSON.parse(stored).token}` };
    }
  } catch {}

  return {};
}

async function apiFetch<T>(
  endpoint: string,
  options?: RequestInit,
  timeoutMs: number = 10000
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const authHeaders = await getAuthHeader();
  const headers: Record<string, string> = { ...authHeaders };

  if (options?.headers) {
    const optHeaders = options.headers as Record<string, string>;
    Object.assign(headers, optHeaders);
    delete options.headers;
  }

  try {
    const url = `${API_BASE}${endpoint}`;
    const res = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });

    if (!res.ok) {
      const body = await res.text();
      let message: string;
      try {
        const json = JSON.parse(body);
        message = json.detail || json.message || body;
      } catch {
        message = body || `Erreur ${res.status}`;
      }
      throw new Error(message);
    }

    return res.json();
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function analyzePhoto(file: File): Promise<AnalysisResult> {
  const formData = new FormData();
  formData.append("fichier", file);
  return apiFetch<AnalysisResult>("/api/analyze", {
    method: "POST",
    body: formData,
  });
}

export async function restorePhoto(file: File, colorize?: boolean): Promise<RestoreResult> {
  const formData = new FormData();
  formData.append("fichier", file);
  if (colorize) {
    formData.append("coloriser", "true");
  }
  return apiFetch<RestoreResult>("/api/restore", {
    method: "POST",
    body: formData,
  }, 60000);
}

export async function colorizePhoto(file: File): Promise<RestoreResult> {
  const formData = new FormData();
  formData.append("fichier", file);
  return apiFetch<RestoreResult>("/api/colorize", {
    method: "POST",
    body: formData,
  }, 60000);
}

export function getRestoredImageUrl(urlImage: string): string {
  if (!urlImage) return "";
  if (urlImage.startsWith("http")) return urlImage;
  const base = typeof window !== "undefined"
    ? window.location.origin
    : process.env.NEXT_PUBLIC_SITE_URL || "https://flashback-restore.com";
  return `${base}${urlImage}`;
}

export function getPhotoUrl(chemin: string): string {
  if (!chemin) return "";
  if (chemin.startsWith("http")) return chemin;
  const filename = chemin.split("/").pop();
  const base = typeof window !== "undefined"
    ? window.location.origin
    : process.env.NEXT_PUBLIC_SITE_URL || "https://flashback-restore.com";
  return `${base}/uploads/${filename}`;
}

export async function animatePhoto(
  file: File,
  text: string
): Promise<AnimateResult> {
  const formData = new FormData();
  formData.append("fichier", file);
  formData.append("texte", text);
  return apiFetch<AnimateResult>("/api/animate", {
    method: "POST",
    body: formData,
  }, 30000);
}

export async function checkAnimationStatus(
  jobId: string
): Promise<AnimationStatus> {
  return apiFetch<AnimationStatus>(`/api/animate/${jobId}`);
}

export async function createCheckout(
  plan: string,
  userEmail: string
): Promise<CheckoutResult> {
  return apiFetch<CheckoutResult>("/api/stripe/create-checkout", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plan, email_utilisateur: userEmail }),
  });
}

export interface UserMe {
  id: string;
  email: string;
  nom: string | null;
  plan: string;
  credits: number;
  credits_utilises: number;
  photos_restaurees_mois: number;
  animations_creees: number;
  animations_utilisees: number;
  animations_limite: number;
  date_renouvellement: string | null;
  est_abonne: boolean;
  essais_restants: number;
  retention_jours: number;
  derniere_activite: string | null;
}

export async function getUserMe(): Promise<UserMe> {
  return apiFetch<UserMe>("/api/user/me");
}

export interface UserHistoryResponse {
  travaux: TravailHistorique[];
  retention_jours: number;
  total: number;
}

export async function getUserHistory(): Promise<UserHistoryResponse> {
  return apiFetch<UserHistoryResponse>("/api/user/history");
}

export interface UserPreferences {
  retention_jours: number;
  options_disponibles: number[];
}

export async function getUserPreferences(): Promise<UserPreferences> {
  return apiFetch<UserPreferences>("/api/user/preferences");
}

export async function updatePreferences(retention_jours: number): Promise<{ message: string; retention_jours: number }> {
  return apiFetch<{ message: string; retention_jours: number }>("/api/user/preferences", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ retention_jours }),
  });
}

export async function deleteTravail(travail_id: string): Promise<{ message: string; fichiers_supprimes: string[] }> {
  return apiFetch<{ message: string; fichiers_supprimes: string[] }>(
    `/api/user/history/${travail_id}`,
    { method: "DELETE" }
  );
}

export async function deleteAllHistory(): Promise<{ message: string; travaux_supprimes: number; fichiers_supprimes: number }> {
  return apiFetch<{ message: string; travaux_supprimes: number; fichiers_supprimes: number }>(
    "/api/user/history",
    { method: "DELETE" }
  );
}

export async function healthCheck(): Promise<{ status: string }> {
  return apiFetch<{ status: string }>("/api/health");
}
