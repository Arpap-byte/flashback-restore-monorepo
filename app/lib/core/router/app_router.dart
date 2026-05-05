import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../constants/app_constants.dart';
import '../../features/home/presentation/screens/home_screen.dart';
import '../../features/home/presentation/screens/splash_screen.dart';
import '../../features/home/presentation/screens/onboarding_screen.dart';
import '../../features/restoration/presentation/screens/restoration_screen.dart';
import '../../features/restoration/presentation/screens/restoration_result_screen.dart';
import '../../features/animation/presentation/screens/animation_screen.dart';
import '../../features/animation/presentation/screens/animation_result_screen.dart';
import '../../features/gallery/presentation/screens/gallery_screen.dart';
import '../../features/gallery/presentation/screens/photo_detail_screen.dart';
import '../../features/settings/presentation/screens/settings_screen.dart';
import '../../features/settings/presentation/screens/purchase_screen.dart';

/// Provider pour le router de l'application
final appRouterProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: AppRoutes.splash,
    debugLogDiagnostics: true,
    routes: [
      // Splash Screen
      GoRoute(
        path: AppRoutes.splash,
        name: 'splash',
        builder: (context, state) => const SplashScreen(),
      ),

      // Onboarding
      GoRoute(
        path: AppRoutes.onboarding,
        name: 'onboarding',
        builder: (context, state) => const OnboardingScreen(),
      ),

      // Main Shell avec Bottom Navigation
      ShellRoute(
        builder: (context, state, child) => MainShell(child: child),
        routes: [
          // Home
          GoRoute(
            path: AppRoutes.home,
            name: 'home',
            builder: (context, state) => const HomeScreen(),
          ),

          // Gallery
          GoRoute(
            path: AppRoutes.gallery,
            name: 'gallery',
            builder: (context, state) => const GalleryScreen(),
            routes: [
              GoRoute(
                path: ':id',
                name: 'photoDetail',
                builder: (context, state) {
                  final photoId = state.pathParameters['id']!;
                  return PhotoDetailScreen(photoId: photoId);
                },
              ),
            ],
          ),

          // Settings
          GoRoute(
            path: AppRoutes.settings,
            name: 'settings',
            builder: (context, state) => const SettingsScreen(),
          ),
        ],
      ),

      // Restoration Flow (hors shell)
      GoRoute(
        path: AppRoutes.restoration,
        name: 'restoration',
        builder: (context, state) => const RestorationScreen(),
      ),
      GoRoute(
        path: AppRoutes.restorationResult,
        name: 'restorationResult',
        builder: (context, state) {
          final extra = state.extra as Map<String, dynamic>?;
          return RestorationResultScreen(
            originalImagePath: extra?['originalPath'] ?? '',
            restoredImagePath: extra?['restoredPath'] ?? '',
          );
        },
      ),

      // Animation Flow (hors shell)
      GoRoute(
        path: AppRoutes.animation,
        name: 'animation',
        builder: (context, state) {
          final extra = state.extra as Map<String, dynamic>?;
          return AnimationScreen(
            imagePath: extra?['imagePath'] ?? '',
          );
        },
      ),
      GoRoute(
        path: AppRoutes.animationResult,
        name: 'animationResult',
        builder: (context, state) {
          final extra = state.extra as Map<String, dynamic>?;
          return AnimationResultScreen(
            originalImagePath: extra?['originalPath'] ?? '',
            animatedVideoPath: extra?['videoPath'] ?? '',
          );
        },
      ),

      // Purchase Screen
      GoRoute(
        path: AppRoutes.purchase,
        name: 'purchase',
        builder: (context, state) => const PurchaseScreen(),
      ),
    ],
    errorBuilder: (context, state) => Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            Text(
              'Page non trouvée',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(state.uri.toString()),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => context.go(AppRoutes.home),
              child: const Text('Retour à l\'accueil'),
            ),
          ],
        ),
      ),
    ),
  );
});

/// Shell principal avec la navigation bottom
class MainShell extends StatelessWidget {
  final Widget child;

  const MainShell({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: child,
      bottomNavigationBar: const MainBottomNavBar(),
    );
  }
}

/// Barre de navigation inférieure
class MainBottomNavBar extends StatelessWidget {
  const MainBottomNavBar({super.key});

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).uri.toString();

    int currentIndex = 0;
    if (location.startsWith(AppRoutes.gallery)) {
      currentIndex = 1;
    } else if (location.startsWith(AppRoutes.settings)) {
      currentIndex = 2;
    }

    return NavigationBar(
      selectedIndex: currentIndex,
      onDestinationSelected: (index) {
        switch (index) {
          case 0:
            context.go(AppRoutes.home);
            break;
          case 1:
            context.go(AppRoutes.gallery);
            break;
          case 2:
            context.go(AppRoutes.settings);
            break;
        }
      },
      destinations: const [
        NavigationDestination(
          icon: Icon(Icons.home_outlined),
          selectedIcon: Icon(Icons.home),
          label: 'Accueil',
        ),
        NavigationDestination(
          icon: Icon(Icons.photo_library_outlined),
          selectedIcon: Icon(Icons.photo_library),
          label: 'Galerie',
        ),
        NavigationDestination(
          icon: Icon(Icons.settings_outlined),
          selectedIcon: Icon(Icons.settings),
          label: 'Paramètres',
        ),
      ],
    );
  }
}
