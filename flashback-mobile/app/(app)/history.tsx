import { useCallback, useState } from 'react'
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  FlatList,
  Image,
  RefreshControl,
  Alert,
  ActivityIndicator,
} from 'react-native'
import { useRouter } from 'expo-router'
import { useQuery } from '@tanstack/react-query'
import { Trash2, ImageOff } from 'lucide-react-native'
import { useTheme } from '../../src/theme/theme'
import { useAPI, type ImageBibliotheque } from '../../src/lib/api'

export default function HistoryScreen() {
  const { colors, spacing, radii } = useTheme()
  const router = useRouter()
  const api = useAPI()
  const [deleting, setDeleting] = useState<string | null>(null)

  const {
    data,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['bibliotheque'],
    queryFn: () => api.bibliotheque(50, 0),
  })

  const handleDelete = useCallback((image: ImageBibliotheque) => {
    Alert.alert(
      'Supprimer',
      `Supprimer "${image.nom_origine}" ?`,
      [
        { text: 'Annuler', style: 'cancel' },
        {
          text: 'Supprimer',
          style: 'destructive',
          onPress: async () => {
            setDeleting(image.id)
            try {
              await api.supprimerImage(image.id)
              refetch()
            } catch {
              Alert.alert('Erreur', 'Impossible de supprimer cette image.')
            } finally {
              setDeleting(null)
            }
          },
        },
      ],
    )
  }, [api, refetch])

  const renderItem = useCallback(({ item }: { item: ImageBibliotheque }) => (
    <TouchableOpacity
      style={[styles.item, { backgroundColor: colors.surface, borderColor: colors.border }]}
      activeOpacity={0.7}
    >
      <Image
        source={{ uri: api.urlImage(item.url) }}
        style={styles.thumb}
        resizeMode="cover"
      />
      <View style={styles.itemInfo}>
        <Text style={[styles.itemName, { color: colors.foreground }]} numberOfLines={1}>
          {item.nom_origine}
        </Text>
        <Text style={[styles.itemDate, { color: colors.muted }]}>
          {new Date(item.cree_le).toLocaleDateString('fr-FR', {
            day: 'numeric',
            month: 'long',
            year: 'numeric',
          })}
        </Text>
        {item.taille_octets && (
          <Text style={[styles.itemSize, { color: colors.muted }]}>
            {Math.round(item.taille_octets / 1024)} KB
          </Text>
        )}
      </View>
      <TouchableOpacity
        style={styles.deleteBtn}
        onPress={() => handleDelete(item)}
        disabled={deleting === item.id}
      >
        {deleting === item.id ? (
          <ActivityIndicator size="small" color={colors.error} />
        ) : (
          <Trash2 size={18} color={colors.error} />
        )}
      </TouchableOpacity>
    </TouchableOpacity>
  ), [colors, api, handleDelete, deleting])

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <FlatList
        data={data?.items ?? []}
        keyExtractor={(item) => item.id}
        renderItem={renderItem}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl
            refreshing={isLoading}
            onRefresh={refetch}
            tintColor={colors.accent}
          />
        }
        ListEmptyComponent={
          !isLoading ? (
            <View style={styles.empty}>
              <ImageOff size={48} color={colors.muted} />
              <Text style={[styles.emptyText, { color: colors.muted }]}>
                Aucune photo restaurée
              </Text>
              <TouchableOpacity
                style={[styles.emptyBtn, { backgroundColor: colors.accent }]}
                onPress={() => router.push('/(app)/restore')}
              >
                <Text style={[styles.emptyBtnText, { color: colors.accentForeground }]}>
                  Restaurer ma première photo
                </Text>
              </TouchableOpacity>
            </View>
          ) : null
        }
        ListHeaderComponent={
          <Text style={[styles.title, { color: colors.foreground }]}>
            Bibliothèque
          </Text>
        }
      />
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  list: { padding: 16, gap: 8 },
  title: { fontSize: 22, fontWeight: '700', marginBottom: 16 },
  item: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
  },
  thumb: {
    width: 56,
    height: 56,
    borderRadius: 8,
  },
  itemInfo: { flex: 1, gap: 2 },
  itemName: { fontSize: 15, fontWeight: '600' },
  itemDate: { fontSize: 13 },
  itemSize: { fontSize: 12 },
  deleteBtn: { padding: 8 },
  empty: {
    alignItems: 'center',
    gap: 12,
    paddingVertical: 60,
  },
  emptyText: { fontSize: 16 },
  emptyBtn: {
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 10,
  },
  emptyBtnText: { fontSize: 15, fontWeight: '600' },
})
