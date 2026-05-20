import { View, Text, TouchableOpacity, StyleSheet, ScrollView } from 'react-native'
import { useAuth, useUser } from '@clerk/clerk-expo'
import { useRouter } from 'expo-router'
import { useTheme } from '../../src/theme/theme'
import { Camera, Image, History, Settings, LogOut } from 'lucide-react-native'

export default function HomeScreen() {
  const { signOut } = useAuth()
  const { user } = useUser()
  const router = useRouter()
  const { colors, spacing } = useTheme()

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.background }]}
      contentContainerStyle={styles.content}
    >
      {/* Header */}
      <Text style={[styles.greeting, { color: colors.foreground }]}>
        Bonjour{user?.firstName ? ` ${user.firstName}` : ''} 👋
      </Text>
      <Text style={[styles.subtitle, { color: colors.muted }]}>
        Que voulez-vous restaurer aujourd'hui ?
      </Text>

      {/* Actions principales */}
      <View style={styles.actions}>
        <TouchableOpacity
          style={[styles.actionCard, { backgroundColor: colors.surface, borderColor: colors.border }]}
          onPress={() => router.push('/(app)/restore')}
        >
          <Camera size={32} color={colors.accent} />
          <Text style={[styles.actionTitle, { color: colors.foreground }]}>Prendre une photo</Text>
          <Text style={[styles.actionDesc, { color: colors.muted }]}>Utiliser l'appareil photo</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.actionCard, { backgroundColor: colors.surface, borderColor: colors.border }]}
          onPress={() => router.push('/(app)/restore?pick=1')}
        >
          <Image size={32} color={colors.accent} />
          <Text style={[styles.actionTitle, { color: colors.foreground }]}>Depuis la galerie</Text>
          <Text style={[styles.actionDesc, { color: colors.muted }]}>Choisir une photo existante</Text>
        </TouchableOpacity>
      </View>

      {/* Menu */}
      <View style={styles.menu}>
        <TouchableOpacity
          style={[styles.menuItem, { borderColor: colors.border }]}
          onPress={() => router.push('/(app)/history')}
        >
          <History size={20} color={colors.foreground} />
          <Text style={[styles.menuText, { color: colors.foreground }]}>Historique</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.menuItem, { borderColor: colors.border }]}
          onPress={() => router.push('/(app)/settings')}
        >
          <Settings size={20} color={colors.foreground} />
          <Text style={[styles.menuText, { color: colors.foreground }]}>Paramètres</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.menuItem, { borderColor: colors.border }]}
          onPress={() => signOut()}
        >
          <LogOut size={20} color={colors.error} />
          <Text style={[styles.menuText, { color: colors.error }]}>Déconnexion</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 24, gap: 24 },
  greeting: { fontSize: 26, fontWeight: '700' },
  subtitle: { fontSize: 16, marginTop: -8 },
  actions: { flexDirection: 'row', gap: 12 },
  actionCard: {
    flex: 1,
    borderWidth: 1,
    borderRadius: 16,
    padding: 20,
    gap: 8,
    alignItems: 'center',
  },
  actionTitle: { fontSize: 14, fontWeight: '600', textAlign: 'center' },
  actionDesc: { fontSize: 12, textAlign: 'center' },
  menu: { gap: 1 },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 16,
    borderBottomWidth: 1,
  },
  menuText: { fontSize: 16 },
})
