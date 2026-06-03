import { Redirect } from 'expo-router'

/**
 * Route racine — point d'entrée de l'application.
 * Redirige vers l'auth, qui gère automatiquement :
 *   - utilisateur non connecté → /(auth)/sign-in
 *   - utilisateur déjà connecté   → /(app)/home
 */
export default function Index() {
  return <Redirect href="/(auth)/sign-in" />
}
