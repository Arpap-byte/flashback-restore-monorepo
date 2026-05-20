import { useSignUp } from '@clerk/clerk-expo'
import { Stack, Link } from 'expo-router'
import { View, Text, TextInput, TouchableOpacity, StyleSheet } from 'react-native'
import { useTheme } from '../../src/theme/theme'
import { useState } from 'react'

export default function SignUpScreen() {
  const { signUp, setActive, isLoaded } = useSignUp()
  const { colors } = useTheme()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const onSignUp = async () => {
    if (!isLoaded) return
    setLoading(true)
    setError('')
    try {
      const result = await signUp.create({ emailAddress: email, password })
      if (result.status === 'complete') {
        await setActive({ session: result.createdSessionId })
      }
    } catch (e: any) {
      setError(e.errors?.[0]?.message || "Erreur d'inscription")
    } finally {
      setLoading(false)
    }
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Stack.Screen options={{ headerShown: false }} />
      <Text style={[styles.title, { color: colors.foreground }]}>
        Créer un compte
      </Text>
      <Text style={[styles.subtitle, { color: colors.muted }]}>
        Rejoignez Flashback Restore
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
        onPress={onSignUp}
        disabled={loading}
      >
        <Text style={[styles.buttonText, { color: colors.accentForeground }]}>
          {loading ? 'Création...' : "S'inscrire"}
        </Text>
      </TouchableOpacity>

      <Link href="/(auth)/sign-in" style={[styles.link, { color: colors.accent }]}>
        Déjà un compte ? Se connecter
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
  link: { textAlign: 'center', fontSize: 14, marginTop: 8 },
})
