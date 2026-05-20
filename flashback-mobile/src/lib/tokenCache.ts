import * as SecureStore from 'expo-secure-store'
import type { TokenCache } from '@clerk/clerk-expo'

// Cache token Clerk dans le secure store natif (Keychain iOS / Keystore Android)
export const tokenCache: TokenCache = {
  async getToken(key: string): Promise<string | null> {
    try {
      const token = await SecureStore.getItemAsync(key)
      return token
    } catch {
      return null
    }
  },
  async saveToken(key: string, token: string): Promise<void> {
    try {
      await SecureStore.setItemAsync(key, token)
    } catch {
      // ignore (ex: SecureStore indisponible dans Expo Go)
    }
  },
}
