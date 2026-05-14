const API_BASE = typeof window === "undefined"
  ? (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
  : (process.env.NEXT_PUBLIC_API_URL || ""); // client : chemin relatif → même domaine HTTPS

/** Erreur API avec code de statut HTTP pour discrimination (ex: 401/403 fatals vs erreurs réseau temporaires) */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

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
  travail_id: string;
}

export interface AnimationStatus {
  status: "en_attente" | "en_cours" | "termine" | "erreur";
  progress?: number;
  result_url?: string;
  url_video?: string;
  message?: string;
  travail_id?: string;
  resolution?: string;
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

/**
 * Extrait le token JWT brut depuis Clerk ou localStorage.
 * Retourne null si aucun token n'est disponible.
 */
async function getAuthToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;

  // 1. Clerk token
  try {
    const clerk = (window as any).Clerk;
    if (clerk?.session) {
      const token = await clerk.session.getToken();
      if (token) return token;
    }
  } catch {}

  // 2. Fallback: localStorage
  try {
    const stored = localStorage.getItem("flashback_auth");
    if (stored) {
      const parsed = JSON.parse(stored);
      return parsed.token || null;
    }
  } catch {}

  return null;
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
      throw new ApiError(message, res.status);
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

export interface RestoreJobResponse {
  jobId: string;
  travailId: string;
  message: string;
}

export async function restorePhoto(file: File, colorize?: boolean, resolution?: string): Promise<RestoreJobResponse> {
  const formData = new FormData();
  formData.append("fichier", file);
  if (colorize) {
    formData.append("coloriser", "true");
  }
  if (resolution) {
    formData.append("resolution", resolution);
  }
  const raw = await apiFetch<{ job_id: string; travail_id: string; message: string }>("/api/restore", {
    method: "POST",
    body: formData,
  }, 60000);
  return { jobId: raw.job_id, travailId: raw.travail_id, message: raw.message };
}

export async function colorizePhoto(file: File): Promise<RestoreResult> {
  const formData = new FormData();
  formData.append("fichier", file);
  return apiFetch<RestoreResult>("/api/colorize", {
    method: "POST",
    body: formData,
  }, 60000);
}

export async function pollRestoreJob(
  jobId: string,
  onProgress?: (msg: string) => void,
  maxWaitMs = 120000,
  signal?: AbortSignal,
): Promise<RestoreResult> {
  const start = Date.now();
  const pollInterval = 2000;

  while (Date.now() - start < maxWaitMs) {
    // Vérifier l'annulation avant chaque itération
    if (signal?.aborted) {
      throw new Error("Polling annulé.");
    }

    const status = await apiFetch<{
      statut: string;
      resultat?: { url_image?: string; message?: string; analyse?: AnalysisResult; credits_consommes?: number };
      message?: string;
    }>(`/api/job/${jobId}`);

    if (status.statut === "termine") {
      const res = status.resultat || {};
      return {
        message: res.message || "Photo restaurée avec succès !",
        analyse: res.analyse || { rayures: false, decoloration: false, taches: false, dechirures: false, bruit: false, etat_global: "restauré", age_estime: "inconnu", recommandations: [] },
        url_image: res.url_image || "",
      };
    }

    if (status.statut === "erreur") {
      throw new Error(status.message || "Erreur lors du traitement de la photo.");
    }

    if (status.statut === "introuvable") {
      throw new Error("Le job de restauration a expiré. Veuillez réessayer.");
    }

    // Still in progress
    const elapsed = Math.round((Date.now() - start) / 1000);
    onProgress?.(`Restauration IA en cours... (${elapsed}s)`);
    await new Promise((r) => setTimeout(r, pollInterval));
    // Re-vérifier après le sleep au cas où l'annulation est survenue pendant l'attente
    if (signal?.aborted) {
      throw new Error("Polling annulé.");
    }
  }

  throw new Error("La restauration a pris trop de temps. Veuillez réessayer.");
}

/**
 * Convertit un chemin serveur en URL publique avec token JWT.
 *
 * Pour les URLs /uploads/ : côté client, ajoute automatiquement ?token=...
 * (contourne l'impossibilité d'envoyer un header Authorization sur les balises <img>).
 * Côté serveur (SSR) : retourne l'URL sans token (pas d'accès au token client).
 *
 * @param chemin - Chemin relatif (ex: "/uploads/abc123.jpg") ou URL absolue
 * @param token  - Token JWT optionnel pré-calculé (évite un appel async supplémentaire)
 */
export function getPhotoUrl(chemin: string, token?: string | null): string {
  if (!chemin) return "";
  if (chemin.startsWith("http")) return chemin;
  const base = typeof window !== "undefined"
    ? window.location.origin
    : process.env.NEXT_PUBLIC_SITE_URL || "https://flashback-restore.com";
  let url = `${base}${chemin}`;
  // Si l'URL contient déjà un ?token= (ajouté par le backend), ne pas en rajouter
  if (typeof window !== "undefined" && token && url.includes("/uploads/") && !url.includes("?token=")) {
    url += `?token=${encodeURIComponent(token)}`;
  }
  return url;
}

/**
 * Version async de getPhotoUrl qui récupère automatiquement le token.
 * À utiliser quand on a besoin d'une URL avec token pour fetch/telechargement.
 */
export async function getPhotoUrlAsync(chemin: string): Promise<string> {
  const token = await getAuthToken();
  return getPhotoUrl(chemin, token);
}

export async function animatePhoto(
  file: File,
  comportement: string = "naturel",
  resolution: string = "720p"
): Promise<AnimateResult> {
  const formData = new FormData();
  formData.append("fichier", file);
  formData.append("comportement", comportement);
  formData.append("resolution", resolution);
  return apiFetch<AnimateResult>("/api/animate", {
    method: "POST",
    body: formData,
  }, 30000);
}

export async function checkAnimationStatus(
  travailId: string
): Promise<AnimationStatus> {
  return apiFetch<AnimationStatus>(`/api/animate/travail/${travailId}`);
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
