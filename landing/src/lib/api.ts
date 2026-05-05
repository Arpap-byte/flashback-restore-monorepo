const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://148.230.116.52:8000";

export interface AnalysisResult {
  scratches: number;
  fading: number;
  stains: number;
  tears: number;
  noise: number;
  condition: string;
  estimated_age: string;
  recommendations: string[];
}

export interface RestoreResult {
  success: boolean;
  filename: string;
  url: string;
}

export interface AnimateResult {
  success: boolean;
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

async function apiFetch<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, options);

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
}

export async function analyzePhoto(file: File): Promise<AnalysisResult> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<AnalysisResult>("/api/analyze", {
    method: "POST",
    body: formData,
  });
}

export async function restorePhoto(file: File): Promise<RestoreResult> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<RestoreResult>("/api/restore", {
    method: "POST",
    body: formData,
  });
}

export function getRestoredImageUrl(filename: string): string {
  return `${API_BASE}/uploads/${filename}`;
}

export async function animatePhoto(
  file: File,
  text: string
): Promise<AnimateResult> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("text", text);
  return apiFetch<AnimateResult>("/api/animate", {
    method: "POST",
    body: formData,
  });
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
    body: JSON.stringify({ plan, user_email: userEmail }),
  });
}

export async function healthCheck(): Promise<{ status: string }> {
  return apiFetch<{ status: string }>("/api/health");
}
