import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ScrollView,
} from 'react-native'
import { useAuth, useUser } from '@clerk/clerk-expo'
import { useRouter } from 'expo-router'
import { LogOut, Shield, CreditCard, Info } from 'lucide-react-native'
import { useTheme } from '../../src/theme/theme'

export default function SettingsScreen() {
  const { signOut } = useAuth()
  const { user } = useUser()
  const router = useRouter()
  const { colors, spacing, radii } = useTheme()

  const handleLogout = () => {
    Alert.alert('Déconnexion', 'Voulez-vous vraiment vous déconnecter ?', [
      { text: 'Annuler', style: 'cancel' },
      {
        text: 'Déconnecter',
        style: 'destructive',
        onPress: () => signOut(),
      },
    ])
  }

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.background }]}
      contentContainerStyle={styles.content}
    >
      <Text style={[styles.title, { color: colors.foreground }]}>Paramètres</Text>

      {/* Profil */}
      <View style={[styles.section, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <Text style={[styles.sectionTitle, { color: colors.foreground }]}>Profil</Text>
        <View style={styles.row}>
          <Text style={[styles.label, { color: colors.muted }]}>Email</Text>
          <Text style={[styles.value, { color: colors.foreground }]}>
            {user?.emailAddresses?.[0]?.emailAddress ?? '—'}
          </Text>
        </View>
        <View style={styles.row}>
          <Text style={[styles.label, { color: colors.muted }]}>Nom</Text>
          <Text style={[styles.value, { color: colors.foreground }]}>
            {user?.firstName ? `${user.firstName} ${user.lastName ?? ''}` : '—'}
          </Text>
        </View>
      </View>

      {/* Compte */}
      <View style={[styles.section, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <Text style={[styles.sectionTitle, { color: colors.foreground }]}>Compte</Text>
        <TouchableOpacity style={styles.menuItem}>
          <CreditCard size={20} color={colors.accent} />
          <Text style={[styles.menuText, { color: colors.foreground }]}>Crédits & abonnement</Text>
          <Text style={[styles.menuArrow, { color: colors.muted }]}>›</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.menuItem}>
          <Shield size={20} color={colors.accent} />
          <Text style={[styles.menuText, { color: colors.foreground }]}>Sécurité</Text>
          <Text style={[styles.menuArrow, { color: colors.muted }]}>›</Text>
        </TouchableOpacity>
      </View>

      {/* À propos */}
      <View style={[styles.section, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <Text style={[styles.sectionTitle, { color: colors.foreground }]}>À propos</Text>
        <View style={styles.row}>
          <Text style={[styles.label, { color: colors.muted }]}>Version</Text>
          <Text style={[styles.value, { color: colors.foreground }]}>1.0.0</Text>
        </View>
        <View style={styles.row}>
          <Text style={[styles.label, { color: colors.muted }]}>Technologie</Text>
          <Text style={[styles.value, { color: colors.foreground }]}>Notre IA</Text>
        </View>
        <TouchableOpacity style={styles.menuItem}>
          <Info size={20} color={colors.accent} />
          <Text style={[styles.menuText, { color: colors.foreground }]}>Conditions d'utilisation</Text>
          <Text style={[styles.menuArrow, { color: colors.muted }]}>›</Text>
        </TouchableOpacity>
      </View>

      {/* Déconnexion */}
      <TouchableOpacity
        style={[styles.logoutBtn, { borderColor: colors.error }]}
        onPress={handleLogout}
      >
        <LogOut size={20} color={colors.error} />
        <Text style={[styles.logoutText, { color: colors.error }]}>Se déconnecter</Text>
      </TouchableOpacity>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 24, gap: 20, paddingBottom: 40 },
  title: { fontSize: 24, fontWeight: '700' },
  section: {
    borderRadius: 14,
    borderWidth: 1,
    padding: 16,
    gap: 12,
  },
  sectionTitle: { fontSize: 14, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5 },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 4,
  },
  label: { fontSize: 15 },
  value: { fontSize: 15, fontWeight: '500' },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: '#374151',
  },
  menuText: { flex: 1, fontSize: 15 },
  menuArrow: { fontSize: 22 },
  logoutBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 14,
    borderRadius: 12,
    borderWidth: 1,
  },
  logoutText: { fontSize: 15, fontWeight: '600' },
})
