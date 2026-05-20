# App Android Flashback Restore — Plan d'implémentation

> **Validé par Opus 4.7** — 20 mai 2026
> **Exécutant** : DeepSeek Pro (React Native + Expo)

---

## Stack technique

| Couche | Choix | Pourquoi |
|---|---|---|
| Framework | Expo SDK 54 (managed) | Build EAS, OTA updates, pas d'Android Studio quotidien |
| Navigation | expo-router v6 (file-based) | Même convention que Next.js |
| State serveur | @tanstack/react-query v5 | Cache, polling, retry |
| State client | zustand v5 | UI state minimal |
| Auth | @clerk/clerk-expo v2 | Même tenant que le web |
| UI | react-native-unistyles v3 | Dark mode natif, perf |
| Images | expo-image v3 | Cache disque LRU |

**Aucune modification backend requise.** ✅

## Phases

| Phase | Description | Durée |
|---|---|---|
| 0 | Setup Expo + librairies | ½ jour |
| 1 | Auth Clerk (sign-in/up, Google OAuth) | 1 jour |
| 2 | Client API (types + fetch avec JWT) | ½ jour |
| 3 | Upload + Restauration | 2 jours |
| 4 | Polling + Résultat (slider avant/après) | 1 jour |
| 5 | Historique | 1 jour |
| 6 | Settings + Dark mode | ½ jour |
| 7 | Build & Play Store | 1 jour |

**Total : 7–8 jours**

## Optimisations clés

- **Compression image** avant upload (12 MB → 600 KB)
- **Polling intelligent** React Query (arrêt si app en background)
- **Cache persistant** AsyncStorage (historique dispo au cold start)
- **Slider 60 fps** Reanimated 4 + GestureHandler
- **Proguard activé** pour réduire la taille de l'APK

## Pièges critiques

1. Stripe in-app → risque rejet Play Store → **v1 sans paiement**
2. FormData RN différent du web
3. OAuth Google ne marche pas dans Expo Go → dev build obligatoire
4. JWT Clerk 60s → getToken() à chaque requête
5. Permissions Android 13+ : READ_MEDIA_IMAGES

## MVP

Auth → Upload → Restauration → Résultat avant/après → Historique → Dark mode
