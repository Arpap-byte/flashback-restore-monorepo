/**
 * Types pour l'API Flashback Restore — alignés sur backend/app/models/schemas.py
 */

// POST /api/restore — réponse
export interface AnalysePhoto {
  rayures: boolean
  decoloration: boolean
  taches: boolean
  dechirures: boolean
  bruit: boolean
  etat_global: 'excellent' | 'bon' | 'moyen' | 'mauvais' | 'très_mauvais'
  age_estime: string
  recommandations: string[]
}

export interface RestaurationReponse {
  message: string
  analyse: AnalysePhoto
  url_image: string
  credits_consommes: number
}

// GET /api/job/{job_id} — polling
export type StatutJob = 'en_attente' | 'en_cours' | 'termine' | 'erreur'

export interface StatutJobReponse {
  job_id: string
  statut: StatutJob
  url_image?: string
  analyse?: AnalysePhoto
  message_erreur?: string
}

// GET /api/stats — admin
export interface StatsReponse {
  nombre_total_utilisateurs: number
  nombre_total_restaurations: number
  nombre_total_animations: number
}
