import { Stack } from 'expo-router'
import { ClerkProvider } from '@clerk/clerk-expo'
import { QueryClientProvider } from '@tanstack/react-query'
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client'
import { StatusBar } from 'expo-status-bar'
import { tokenCache } from '../src/lib/tokenCache'
import { queryClient, asyncStoragePersister } from '../src/lib/queryClient'
import { ThemeProvider } from '../src/theme/theme'
import { theme } from '../src/theme/theme'

const CLERK_KEY = process.env.EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY!

export default function RootLayout() {
  return (
    <ClerkProvider tokenCache={tokenCache} publishableKey={CLERK_KEY}>
      <PersistQueryClientProvider
        client={queryClient}
        persistOptions={{ persister: asyncStoragePersister }}
      >
        <ThemeProvider value={theme}>
          <StatusBar style="light" />
          <Stack screenOptions={{ headerShown: false }}>
            <Stack.Screen name="(auth)" options={{ headerShown: false }} />
            <Stack.Screen name="(app)" options={{ headerShown: false }} />
          </Stack>
        </ThemeProvider>
      </PersistQueryClientProvider>
    </ClerkProvider>
  )
}
