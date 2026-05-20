import { Stack, Redirect } from 'expo-router'
import { useAuth } from '@clerk/clerk-expo'

export default function AuthLayout() {
  const { isSignedIn } = useAuth()

  // Déjà connecté → rediriger vers l'app
  if (isSignedIn) return <Redirect href="/(app)/home" />

  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="sign-in" />
      <Stack.Screen name="sign-up" />
    </Stack>
  )
}
