# Application Mobile Flashback Restore

Application Flutter de restauration et d'animation de photos anciennes par IA.

## Prérequis

- Flutter SDK >= 3.2.0
- Dart SDK >= 3.2.0
- Android Studio ou Xcode (selon la plateforme cible)
- Le backend FastAPI doit être en cours d'exécution (voir `/backend/`)

## Installation

```bash
# Se placer dans le répertoire de l'application
cd app/

# Installer les dépendances Flutter
flutter pub get

# Générer le code (freezed, json_serializable, riverpod)
flutter pub run build_runner build --delete-conflicting-outputs
```

## Configuration du backend

L'URL du backend est configurée dans `lib/core/constants/app_constants.dart` :

```dart
static const String apiBaseUrl = 'http://localhost:8000';
```

**En développement local :** laissez la valeur par défaut `http://localhost:8000`.
Assurez-vous que le backend FastAPI tourne sur le port 8000.

**Sur un appareil physique** (Android/iOS) connecté au même réseau :

```dart
// Remplacez localhost par l'IP locale de votre machine
static const String apiBaseUrl = 'http://192.168.1.XX:8000';
```

**En production :** utilisez l'URL HTTPS de votre backend déployé :

```dart
static const String apiBaseUrl = 'https://api.flashback-restore.com';
```

Vous pouvez également changer l'URL dynamiquement via le service API :

```dart
ref.read(apiServiceProvider).setBaseUrl('https://nouvelle-url.com');
```

## Lancement

```bash
# Lancer sur un appareil/émulateur connecté
flutter run

# Lancer avec un profil de build spécifique
flutter run --debug    # Mode debug (par défaut)
flutter run --profile  # Mode profilage
flutter run --release  # Mode production
```

## Architecture

```
lib/
├── core/                   # Fondations de l'application
│   ├── constants/          # Constantes globales, URLs, clés de stockage
│   ├── router/             # Configuration GoRouter (navigation)
│   └── theme/              # Thèmes clair et sombre, palette de couleurs
├── features/               # Fonctionnalités (architecture feature-first)
│   ├── animation/          # Animation de photos (style Harry Potter)
│   └── presentation/screens/
│       ├── animation_screen.dart
│       └── animation_result_screen.dart
│   ├── gallery/            # Galerie de photos
│   │   └── presentation/screens/
│   │       ├── gallery_screen.dart
│   │       └── photo_detail_screen.dart
│   ├── home/               # Écrans d'accueil, onboarding, splash
│   │   └── presentation/screens/
│   │       ├── home_screen.dart
│   │       ├── onboarding_screen.dart
│   │       └── splash_screen.dart
│   ├── restoration/        # Restauration de photos
│   │   └── presentation/screens/
│   │       ├── restoration_screen.dart
│   │       └── restoration_result_screen.dart
│   └── settings/           # Paramètres et achats in-app
│       └── presentation/screens/
│           ├── settings_screen.dart
│           └── purchase_screen.dart
├── shared/                 # Code partagé entre les features
│   ├── models/             # Modèles de données (Photo, User, Purchase)
│   └── services/           # Services métier
│       ├── api_service.dart         # Communication avec le backend FastAPI
│       ├── gemini_service.dart      # Analyse/restauration IA (backend ou direct)
│       ├── animation_service.dart   # Animation D-ID (backend ou direct)
│       ├── purchase_service.dart    # Achats in-app RevenueCat
│       └── storage_service.dart     # Stockage local (Hive + SharedPreferences)
└── main.dart               # Point d'entrée de l'application
```

### Services clés

| Service | Rôle | Backend |
|---------|------|---------|
| `ApiService` | Client HTTP unique vers le backend FastAPI | POST/GET /api/* |
| `GeminiService` | Analyse et restauration de photos | `/api/analyze`, `/api/restore` |
| `AnimationService` | Animation de photos | `/api/animate`, `/api/animate/{id}` |
| `PurchaseService` | Achats in-app via RevenueCat | N/A (direct) |
| `StorageService` | Persistance locale (Hive + SharedPrefs) | N/A (local) |

### State Management

- **[Riverpod](https://riverpod.dev/)** pour la gestion d'état réactive
- Architecture **Provider** avec des singletons pour les services
- `FutureProvider` pour les données asynchrones

### Navigation

- **[GoRouter](https://pub.dev/packages/go_router)** avec un `ShellRoute` pour la barre de navigation inférieure
- Routes full-screen pour les flux restoration/animation

## Compilation pour la production

```bash
# Android (APK)
flutter build apk --release

# Android (App Bundle - recommandé pour le Play Store)
flutter build appbundle --release

# iOS (nécessite macOS + Xcode)
flutter build ios --release
```

## Notes importantes

- **Firebase et Hive sont temporairement désactivés** (commentés dans `main.dart`)
  pour permettre la compilation pendant la phase de migration.
- Les services `GeminiService` et `AnimationService` peuvent fonctionner
  soit via le backend FastAPI (`useBackend = true`, par défaut),
  soit en appel direct les SDK/APIs externes (`useBackend = false`).
- La clé API Gemini dans `gemini_service.dart` n'est utilisée qu'en mode
  `useBackend = false` (fallback direct). En production, toutes les requêtes
  doivent passer par le backend.

---

👤 Développé pour **Seb (Arpap)** — Projet Flashback Restore
