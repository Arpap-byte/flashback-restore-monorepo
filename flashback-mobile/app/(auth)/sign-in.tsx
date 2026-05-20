import { useSignIn, useOAuth } from '@clerk/clerk-expo'
import { Stack, Link } from 'expo-router'
import { View, Text, TextInput, TouchableOpacity, StyleSheet } from 'react-native'
import { useTheme } from '../../src/theme/theme'
import { useState } from 'react'
import * as WebBrowser from 'expo-web-browser'

// Warm up browser for OAuth
WebBrowser.maybeCompleteAuthSession()

export default function SignInScreen() {
  const { signIn, setActive, isLoaded } = useSignIn()
  const { startOAuthFlow } = useOAuth({ strategy: 'oauth_google' })
  const { colors } = useTheme()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const onSignIn = async () => {
    if (!isLoaded) return
    setLoading(true)
    setError('')
    try {
      const result = await signIn.create({ identifier: email, password })
      if (result.status === 'complete') {
        await setActive({ session: result.createdSessionId })
      }
    } catch (e: any) {
      setError(e.errors?.[0]?.message || 'Erreur de connexion')
    } finally {
      setLoading(false)
    }
  }

  const onGoogleSignIn = async () => {
    setError('')
    try {
      const { createdSessionId, setActive: setOAuthActive } = await startOAuthFlow({
        redirectUrl: 'flashbackrestore://oauth-native-callback',
      })
      if (createdSessionId && setOAuthActive) {
        await setOAuthActive({ session: createdSessionId })
      }
    } catch (e: any) {
      setError(e.message || "Erreur de connexion Google")
    }
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Stack.Screen options={{ headerShown: false }} />
      <Text style={[styles.title, { color: colors.foreground }]}>
        Flashback Restore
      </Text>
      <Text style={[styles.subtitle, { color: colors.muted }]}>
        Redonnez vie à vos souvenirs
      </Text>

      {error ? (
        <Text style={[styles.error, { color: colors.error }]}>{error}</Text>
      ) : null}

      <TextInput
        style={[styles.input, { backgroundColor: colors.input, color: colors.inputForeground, borderColor: colors.border }]}
        placeholder="Email"
        placeholderTextColor={colors.muted}
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        keyboardType="email-address"
      />
      <TextInput
        style={[styles.input, { backgroundColor: colors.input, color: colors.inputForeground, borderColor: colors.border }]}
        placeholder="Mot de passe"
        placeholderTextColor={colors.muted}
        value={password}
        onChangeText={setPassword}
        secureTextEntry
      />

      <TouchableOpacity
        style={[styles.button, { backgroundColor: colors.accent }]}
        onPress={onSignIn}
        disabled={loading}
      >
        <Text style={[styles.buttonText, { color: colors.accentForeground }]}>
          {loading ? 'Connexion...' : 'Se connecter'}
        </Text>
      </TouchableOpacity>

      {/* Divider */}
      <View style={styles.divider}>
        <View style={[styles.dividerLine, { backgroundColor: colors.border }]} />
        <Text style={[styles.dividerText, { color: colors.muted }]}>ou</Text>
        <View style={[styles.dividerLine, { backgroundColor: colors.border }]} />
      </View>

      {/* Google OAuth */}
      <TouchableOpacity
        style={[styles.googleButton, { borderColor: colors.border }]}
        onPress={onGoogleSignIn}
      >
        <Text style={[styles.googleButtonText, { color: colors.foreground }]}>
          G  Continuer avec Google
        </Text>
      </TouchableOpacity>

      <Link href="/(auth)/sign-up" style={[styles.link, { color: colors.accent }]}>
        Pas encore de compte ? S'inscrire
      </Link>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', padding: 24, gap: 16 },
  title: { fontSize: 28, fontWeight: '700', textAlign: 'center' },
  subtitle: { fontSize: 16, textAlign: 'center', marginBottom: 16 },
  error: { fontSize: 14, textAlign: 'center', padding: 8 },
  input: { borderWidth: 1, borderRadius: 12, padding: 14, fontSize: 16 },
  button: { borderRadius: 9999, padding: 16, alignItems: 'center', marginTop: 8 },
  buttonText: { fontSize: 16, fontWeight: '600' },
  divider: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  dividerLine: { flex: 1, height: 1 },
  dividerText: { fontSize: 14 },
  googleButton: { borderWidth: 1, borderRadius: 9999, padding: 16, alignItems: 'center' },
  googleButtonText: { fontSize: 16, fontWeight: '500' },
  link: { textAlign: 'center', fontSize: 14 },
})
