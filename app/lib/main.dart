import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
// Firebase et Hive temporairement désactivés pendant la migration vers le monorepo
// import 'package:firebase_core/firebase_core.dart';
// import 'package:hive_flutter/hive_flutter.dart';

import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';
import 'shared/services/purchase_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // TODO(Seb): Réactiver Firebase après la migration et configuration
  // await Firebase.initializeApp();

  // TODO(Seb): Réactiver Hive après la migration
  // await Hive.initFlutter();

  // Initialize RevenueCat for in-app purchases
  await PurchaseService.initialize();

  // Set preferred orientations
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  // Set system UI overlay style
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.dark,
    ),
  );

  runApp(
    const ProviderScope(
      child: FlashbackRestoreApp(),
    ),
  );
}

class FlashbackRestoreApp extends ConsumerWidget {
  const FlashbackRestoreApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(appRouterProvider);

    return MaterialApp.router(
      title: 'Flashback Restore',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: ThemeMode.system,
      routerConfig: router,
    );
  }
}
