import { useState } from 'react'
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Image,
  ScrollView,
  Dimensions,
} from 'react-native'
import { useRouter, useLocalSearchParams } from 'expo-router'
import { Download, Home, Share2 } from 'lucide-react-native'
import { useTheme } from '../../src/theme/theme'
import type { AnalysePhoto } from '../../src/types/api'

const { width: SCREEN_WIDTH } = Dimensions.get('window')
const IMAGE_WIDTH = SCREEN_WIDTH - 48

export default function ResultScreen() {
  const { colors, spacing } = useTheme()
  const router = useRouter()
  const params = useLocalSearchParams<{
    original: string
    restored: string
    analyse: string
    credits: string
  }>()

  const analyse: AnalysePhoto | null = params.analyse
    ? JSON.parse(params.analyse)
    : null
  const [showRestored, setShowRestored] = useState(true)

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.background }]}
      contentContainerStyle={styles.content}
    >
      {/* Titre */}
      <Text style={[styles.title, { color: colors.foreground }]}>
        ✨ Restauration terminée
      </Text>
      <Text style={[styles.subtitle, { color: colors.muted }]}>
        {analyse?.age_estime
          ? `Photo de ${analyse.age_estime} restaurée avec succès`
          : 'Votre photo a été restaurée avec succès'}
      </Text>

      {/* Avant / Après — toggle */}
      <View style={styles.comparison}>
        <View style={[styles.imageCard, { backgroundColor: colors.surface, borderColor: colors.border }]}>
          <Image
            source={{ uri: showRestored ? params.restored : params.original }}
            style={styles.image}
            resizeMode="contain"
          />
          <View style={styles.badge}>
            <Text style={styles.badgeText}>
              {showRestored ? 'Après' : 'Avant'}
            </Text>
          </View>
        </View>

        {/* Toggle */}
        <View style={styles.toggleRow}>
          <TouchableOpacity
            style={[
              styles.toggleBtn,
              !showRestored && { backgroundColor: colors.accent },
            ]}
            onPress={() => setShowRestored(false)}
          >
            <Text
              style={[
                styles.toggleText,
                !showRestored && { color: colors.accentForeground },
                { color: !showRestored ? colors.accentForeground : colors.muted },
              ]}
            >
              Original
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[
              styles.toggleBtn,
              showRestored && { backgroundColor: colors.accent },
            ]}
            onPress={() => setShowRestored(true)}
          >
            <Text
              style={[
                styles.toggleText,
                showRestored && { color: colors.accentForeground },
                { color: showRestored ? colors.accentForeground : colors.muted },
              ]}
            >
              Restaurée
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Analyse IA */}
      {analyse && (
        <View style={[styles.analyseCard, { backgroundColor: colors.surface, borderColor: colors.border }]}>
          <Text style={[styles.sectionTitle, { color: colors.foreground }]}>
            🔍 Analyse de l'IA
          </Text>
          <View style={styles.defects}>
            {[
              { label: 'Rayures', found: analyse.rayures },
              { label: 'Décoloration', found: analyse.decoloration },
              { label: 'Taches', found: analyse.taches },
              { label: 'Déchirures', found: analyse.dechirures },
              { label: 'Bruit', found: analyse.bruit },
            ].map(({ label, found }) => (
              <View key={label} style={styles.defectRow}>
                <Text style={[styles.defectIcon, { color: found ? colors.success : colors.muted }]}>
                  {found ? '✓' : '—'}
                </Text>
                <Text style={[styles.defectLabel, { color: colors.foreground }]}>
                  {label}
                </Text>
              </View>
            ))}
          </View>
          {analyse.recommandations.length > 0 && (
            <>
              <Text style={[styles.recoTitle, { color: colors.muted }]}>
                Recommandations :
              </Text>
              {analyse.recommandations.map((r, i) => (
                <Text key={i} style={[styles.reco, { color: colors.muted }]}>
                  • {r}
                </Text>
              ))}
            </>
          )}
        </View>
      )}

      {/* Crédits */}
      <Text style={[styles.credits, { color: colors.muted }]}>
        Crédits utilisés : {params.credits || '1'}
      </Text>

      {/* Actions */}
      <View style={styles.actions}>
        <TouchableOpacity
          style={[styles.actionBtn, { backgroundColor: colors.accent }]}
          onPress={() => router.replace('/(app)/home')}
        >
          <Home size={20} color={colors.accentForeground} />
          <Text style={[styles.actionText, { color: colors.accentForeground }]}>
            Accueil
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.actionBtn, styles.outline, { borderColor: colors.border }]}
          onPress={() => router.push('/(app)/restore')}
        >
          <Text style={[styles.actionText, { color: colors.foreground }]}>
            Nouvelle photo
          </Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 24, gap: 20, paddingBottom: 60 },
  title: { fontSize: 24, fontWeight: '700', textAlign: 'center' },
  subtitle: { fontSize: 15, textAlign: 'center' },
  comparison: { gap: 12 },
  imageCard: {
    borderRadius: 16,
    borderWidth: 1,
    overflow: 'hidden',
    position: 'relative',
  },
  image: {
    width: IMAGE_WIDTH,
    aspectRatio: 3 / 4,
  },
  badge: {
    position: 'absolute',
    top: 12,
    left: 12,
    backgroundColor: 'rgba(0,0,0,0.7)',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 8,
  },
  badgeText: { color: '#fff', fontSize: 13, fontWeight: '600' },
  toggleRow: {
    flexDirection: 'row',
    gap: 8,
  },
  toggleBtn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: 'center',
  },
  toggleText: { fontSize: 14, fontWeight: '600' },
  analyseCard: {
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    gap: 10,
  },
  sectionTitle: { fontSize: 16, fontWeight: '600' },
  defects: { gap: 6 },
  defectRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  defectIcon: { fontSize: 16, width: 24 },
  defectLabel: { fontSize: 14 },
  recoTitle: { fontSize: 13, marginTop: 4 },
  reco: { fontSize: 13, lineHeight: 20 },
  credits: { fontSize: 13, textAlign: 'center' },
  actions: { flexDirection: 'row', gap: 12 },
  actionBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 14,
    borderRadius: 12,
  },
  outline: { borderWidth: 1 },
  actionText: { fontSize: 15, fontWeight: '600' },
})
