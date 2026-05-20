import { useState, useCallback } from 'react'
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Image,
  ActivityIndicator,
  Alert,
  ScrollView,
} from 'react-native'
import * as ExpoImagePicker from 'expo-image-picker'
import * as ImageManipulator from 'expo-image-manipulator'
import { useRouter, useLocalSearchParams } from 'expo-router'
import { Camera, RotateCcw, Wand2 } from 'lucide-react-native'
import { useTheme } from '../../src/theme/theme'
import { useAPI } from '../../src/lib/api'

export default function RestoreScreen() {
  const { colors, spacing, radii } = useTheme()
  const router = useRouter()
  const { pick } = useLocalSearchParams<{ pick?: string }>()
  const api = useAPI()

  const [imageUri, setImageUri] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // ─── Ouvrir la caméra ──────────────────────────────────────────────
  const openCamera = useCallback(async () => {
    const { status } = await ExpoImagePicker.requestCameraPermissionsAsync()
    if (status !== 'granted') {
      Alert.alert('Permission refusée', 'Activez l’accès caméra dans les réglages.')
      return
    }
    const result = await ExpoImagePicker.launchCameraAsync({
      mediaTypes: ['images'],
      quality: 0.8,
      allowsEditing: true,
      aspect: [3, 4],
    })
    if (!result.canceled && result.assets[0]) {
      setImageUri(result.assets[0].uri)
      setError(null)
    }
  }, [])

  // ─── Ouvrir la galerie ─────────────────────────────────────────────
  const openGallery = useCallback(async () => {
    const { status } = await ExpoImagePicker.requestMediaLibraryPermissionsAsync()
    if (status !== 'granted') {
      Alert.alert('Permission refusée', 'Activez l’accès à la galerie dans les réglages.')
      return
    }
    const result = await ExpoImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      quality: 0.8,
      allowsEditing: true,
      aspect: [3, 4],
    })
    if (!result.canceled && result.assets[0]) {
      setImageUri(result.assets[0].uri)
      setError(null)
    }
  }, [])

  // ─── Lancer automatiquement caméra ou galerie selon le paramètre ──
  const startPicker = useCallback(() => {
    if (pick === '1') openGallery()
    else openCamera()
  }, [pick, openCamera, openGallery])

  // ─── Upload et restauration ────────────────────────────────────────
  const handleRestore = useCallback(async () => {
    if (!imageUri) return
    setUploading(true)
    setError(null)

    try {
      // Compression : max 1200px côté long → ~300-600 KB
      const compressed = await ImageManipulator.manipulateAsync(
        imageUri,
        [{ resize: { width: 1200 } }],
        { compress: 0.7, format: ImageManipulator.SaveFormat.JPEG },
      )

      const result = await api.restaurer(compressed.uri)
      router.replace({
        pathname: '/(app)/result',
        params: {
          original: imageUri,
          restored: api.urlImage(result.url_image),
          analyse: JSON.stringify(result.analyse),
          credits: result.credits_consommes,
        },
      })
    } catch (err: any) {
      setError(err.message || 'Erreur lors de la restauration')
    } finally {
      setUploading(false)
    }
  }, [imageUri, api, router])

  // ─── Réinitialiser ─────────────────────────────────────────────────
  const reset = useCallback(() => {
    setImageUri(null)
    setError(null)
  }, [])

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.background }]}
      contentContainerStyle={styles.content}
    >
      {/* Header */}
      <Text style={[styles.title, { color: colors.foreground }]}>
        Restaurer une photo
      </Text>
      <Text style={[styles.subtitle, { color: colors.muted }]}>
        Notre IA corrige rayures, décoloration, taches et déchirures
      </Text>

      {/* Zone image */}
      {imageUri ? (
        <View style={[styles.previewCard, { backgroundColor: colors.surface, borderColor: colors.border }]}>
          <Image source={{ uri: imageUri }} style={styles.preview} resizeMode="contain" />
          {/* Actions */}
          {!uploading && (
            <View style={styles.previewActions}>
              <TouchableOpacity
                style={[styles.btn, styles.btnOutline, { borderColor: colors.border }]}
                onPress={reset}
              >
                <RotateCcw size={18} color={colors.muted} />
                <Text style={[styles.btnText, { color: colors.muted }]}>Reprendre</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.btn, { backgroundColor: colors.accent }]}
                onPress={handleRestore}
              >
                <Wand2 size={18} color={colors.accentForeground} />
                <Text style={[styles.btnText, { color: colors.accentForeground }]}>
                  Restaurer
                </Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      ) : (
        <TouchableOpacity
          style={[styles.picker, { backgroundColor: colors.surface, borderColor: colors.border }]}
          onPress={startPicker}
        >
          <Camera size={48} color={colors.muted} />
          <Text style={[styles.pickerText, { color: colors.muted }]}>
            {pick === '1'
              ? 'Appuyez pour choisir une photo'
              : 'Appuyez pour prendre une photo'}
          </Text>
        </TouchableOpacity>
      )}

      {/* Upload progress */}
      {uploading && (
        <View style={styles.loading}>
          <ActivityIndicator size="large" color={colors.accent} />
          <Text style={[styles.loadingText, { color: colors.muted }]}>
            Restauration en cours...
          </Text>
          <Text style={[styles.loadingHint, { color: colors.muted }]}>
            Cela peut prendre 30 à 60 secondes
          </Text>
        </View>
      )}

      {/* Erreur */}
      {error && (
        <View style={[styles.errorCard, { backgroundColor: '#7f1d1d', borderColor: colors.error }]}>
          <Text style={[styles.errorText, { color: colors.error }]}>{error}</Text>
          <TouchableOpacity onPress={reset}>
            <Text style={{ color: colors.foreground, fontWeight: '600' }}>Réessayer</Text>
          </TouchableOpacity>
        </View>
      )}
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 24, gap: 20 },
  title: { fontSize: 24, fontWeight: '700' },
  subtitle: { fontSize: 15, lineHeight: 22 },
  picker: {
    aspectRatio: 3 / 4,
    borderRadius: 16,
    borderWidth: 2,
    borderStyle: 'dashed',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  pickerText: { fontSize: 15 },
  previewCard: {
    borderRadius: 16,
    borderWidth: 1,
    overflow: 'hidden',
  },
  preview: {
    width: '100%',
    aspectRatio: 3 / 4,
  },
  previewActions: {
    flexDirection: 'row',
    gap: 12,
    padding: 16,
  },
  btn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 14,
    borderRadius: 12,
  },
  btnOutline: { borderWidth: 1 },
  btnText: { fontSize: 15, fontWeight: '600' },
  loading: { alignItems: 'center', gap: 8, paddingVertical: 20 },
  loadingText: { fontSize: 16, fontWeight: '600' },
  loadingHint: { fontSize: 13 },
  errorCard: {
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    gap: 8,
    alignItems: 'center',
  },
  errorText: { fontSize: 14, textAlign: 'center' },
})
