const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://148.230.116.52:8000";

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
  parametres: {
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
  chemin_photo: string | null;
  chemin_resultat: string | null;
  message_erreur: string | null;
  cree_le: string;
}

/** Get the NextAuth JWT for authenticating API calls */
async function getAuthHeader(): Promise<Record<string, string>> {
  if (typeof window === "undefined") return {};

  try {
    const { getSession } = await import("next-auth/react");
    const session = await getSession();
    const jwt = (session as any)?.jwt;
    if (jwt) {
      return { Authorization: `Bearer ${jwt}` };
    }
  } catch {}

  // Fallback: localStorage token (legacy email/password auth)
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

export async function restorePhoto(file: File): Promise<RestoreResult> {
  const formData = new FormData();
  formData.append("fichier", file);
  return apiFetch<RestoreResult>("/api/restore", {
    method: "POST",
    body: formData,
  }, 30000);
}

export function getRestoredImageUrl(urlImage: string): string {
  return `${API_BASE}${urlImage}`;
}

export function getPhotoUrl(chemin: string): string {
  if (chemin.startsWith("http")) return chemin;
  return `${API_BASE}/uploads/${chemin.split("/").pop()}`;
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

export async function getUserHistory(): Promise<{ travaux: TravailHistorique[] }> {
  return apiFetch<{ travaux: TravailHistorique[] }>("/api/user/history");
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
  date_renouvellement: string | null;
  est_abonne: boolean;
  essais_restants: number;
}

export async function getUserMe(): Promise<UserMe> {
  return apiFetch<UserMe>("/api/user/me");
}

export async function healthCheck(): Promise<{ status: string }> {
  return apiFetch<{ status: string }>("/api/health");
}
