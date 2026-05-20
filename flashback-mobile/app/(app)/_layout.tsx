import { Stack, Redirect } from 'expo-router'
import { useAuth } from '@clerk/clerk-expo'
import { View, ActivityIndicator } from 'react-native'
import { useTheme } from '../../src/theme/theme'

export default function AppLayout() {
  const { isSignedIn, isLoaded } = useAuth()
  const { colors } = useTheme()

  if (!isLoaded) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: colors.background }}>
        <ActivityIndicator size="large" color={colors.accent} />
      </View>
    )
  }

  if (!isSignedIn) return <Redirect href="/(auth)/sign-in" />

  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="home" />
      <Stack.Screen name="restore" />
      <Stack.Screen name="history" />
      <Stack.Screen name="settings" />
    </Stack>
  )
}
