/**
 * Client API Flashback Restore — authentifié via Clerk JWT.
 *
 * Règle : le JWT Clerk expire en 60s → getToken() à chaque requête.
 */

import { useAuth } from '@clerk/clerk-expo'
import type { RestaurationReponse, StatutJobReponse } from '../types/api'

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'https://flashback-restore.com'

/** Obtient un token Clerk frais et appelle l'API */
async function fetchAPI<T>(
  getToken: () => Promise<string | null>,
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = await getToken()
  const url = `${API_URL}${path}`

  const res = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      Authorization: `Bearer ${token}`,
    },
  })

  if (!res.ok) {
    const body = await res.text().catch(() => 'Erreur inconnue')
    throw new Error(`API ${res.status}: ${body}`)
  }

  return res.json()
}

/** Type pour un élément de la bibliothèque */
export interface ImageBibliotheque {
  id: string
  chemin_fichier: string
  nom_origine: string
  mime_type?: string
  taille_octets?: number
  cree_le: string
  url: string
}

export interface BibliothequeReponse {
  items: ImageBibliotheque[]
  limite: number
  offset: number
}

// ─── Hook React : useAPI ───────────────────────────────────────────────────

export function useAPI() {
  const { getToken } = useAuth()

  return {
    /** Upload et restauration d'une photo */
    restaurer: async (
      uri: string,
      options?: { coloriser?: boolean; resolution?: '720p' | '1080p' | '4k' },
    ): Promise<RestaurationReponse> => {
      const formData = new FormData()

      // React Native FormData : on passe l'URI + type MIME
      formData.append('fichier', {
        uri,
        type: 'image/jpeg',
        name: 'photo.jpg',
      } as any)

      if (options?.coloriser) formData.append('coloriser', 'true')
      if (options?.resolution) formData.append('resolution', options.resolution)

      return fetchAPI<RestaurationReponse>(
        getToken,
        '/api/restore',
        { method: 'POST', body: formData },
      )
    },

    /** Polling du statut d'un job */
    statutJob: (jobId: string): Promise<StatutJobReponse> =>
      fetchAPI<StatutJobReponse>(getToken, `/api/job/${jobId}`),

    /** Bibliothèque : liste paginée des images */
    bibliotheque: (limite = 20, offset = 0): Promise<BibliothequeReponse> =>
      fetchAPI<BibliothequeReponse>(
        getToken,
        `/api/library?limite=${limite}&offset=${offset}`,
      ),

    /** Supprimer une image de la bibliothèque */
    supprimerImage: (imageId: string): Promise<void> =>
      fetchAPI<void>(getToken, `/api/library/${imageId}`, { method: 'DELETE' }),

    /** Récupérer l'URL complète d'une image (gère chemins relatifs) */
    urlImage: (path: string): string =>
      path.startsWith('http') ? path : `${API_URL}/${path}`,
  }
}
