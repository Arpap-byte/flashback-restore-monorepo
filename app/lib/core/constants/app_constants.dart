/// Constantes globales de l'application
class AppConstants {
  AppConstants._();

  // ============ APP INFO ============
  static const String appName = 'Flashback Restore';
  static const String appVersion = '1.0.0';
  static const String appBundleId = 'com.flashback.restore';

  // ============ API ENDPOINTS ============
  /// URL de base du backend FastAPI (configurable selon l'environnement).
  /// - Développement local : http://localhost:8000
  /// - Appareil physique (même réseau) : http://<IP_LOCALE>:8000
  /// - Production : https://api.flashback-restore.com
  static const String apiBaseUrl = 'http://localhost:8000';

  static const String geminiBaseUrl = 'https://generativelanguage.googleapis.com';
  static const String animationApiBaseUrl = 'https://api.d-id.com'; // D-ID pour l'animation

  // ============ STORAGE KEYS ============
  static const String keyOnboardingComplete = 'onboarding_complete';
  static const String keyUserToken = 'user_token';
  static const String keyUserId = 'user_id';
  static const String keyDarkMode = 'dark_mode';
  static const String keyLanguage = 'language';
  static const String keyFreeRestorationsUsed = 'free_restorations_used';

  // ============ LIMITS ============
  static const int freeRestorationsLimit = 3;
  static const int maxImageSizeMB = 10;
  static const int animationDurationSeconds = 5;

  // ============ TIMEOUTS ============
  static const Duration apiTimeout = Duration(seconds: 60);
  static const Duration animationTimeout = Duration(seconds: 120);

  // ============ REVENUECAT IDS ============
  static const String rcApiKeyAndroid = 'YOUR_REVENUECAT_ANDROID_KEY';
  static const String rcApiKeyIOS = 'YOUR_REVENUECAT_IOS_KEY';

  // ============ ABONNEMENTS (Stripe) ============
  static const String planDecouverte = 'decouverte';
  static const String planPremium = 'premium';
  static const String planAnnuel = 'annuel';
  static const String planPro = 'pro';

  // ============ PRODUCT IDS (RevenueCat) ============
  static const String productDecouverteMonthly = 'decouverte_monthly';
  static const String productPremiumMonthly = 'premium_monthly';
  static const String productPremiumYearly = 'premium_yearly';
  static const String productPro = 'pro_enterprise';

  // ============ PRICING ============
  static const String priceDecouverte = '4,99 €/mois';
  static const String pricePremium = '29 €/mois';
  static const String priceAnnuel = '249 €/an';
  static const String pricePro = 'Sur mesure';

  // ============ LIMITES PAR PLAN ============
  static const int limitGratuitRestaurations = 3;
  static const int limitGratuitAnimations = 0;
  static const int limitDecouverteRestaurations = 10;
  static const int limitDecouverteAnimations = 3;
  static const int limitPremiumRestaurations = 100;
  static const int limitPremiumAnimations = 30;
}

/// Routes de l'application
class AppRoutes {
  AppRoutes._();

  static const String splash = '/';
  static const String onboarding = '/onboarding';
  static const String home = '/home';
  static const String restoration = '/restoration';
  static const String restorationResult = '/restoration/result';
  static const String animation = '/animation';
  static const String animationResult = '/animation/result';
  static const String gallery = '/gallery';
  static const String photoDetail = '/gallery/:id';
  static const String settings = '/settings';
  static const String purchase = '/purchase';
  static const String about = '/about';
}

/// Assets paths
class AppAssets {
  AppAssets._();

  // Images
  static const String logo = 'assets/images/logo.png';
  static const String logoLight = 'assets/images/logo_light.png';
  static const String onboarding1 = 'assets/images/onboarding_1.png';
  static const String onboarding2 = 'assets/images/onboarding_2.png';
  static const String onboarding3 = 'assets/images/onboarding_3.png';
  static const String placeholder = 'assets/images/placeholder.png';
  static const String emptyGallery = 'assets/images/empty_gallery.png';

  // Icons
  static const String iconRestore = 'assets/images/icon_restore.svg';
  static const String iconAnimate = 'assets/images/icon_animate.svg';
  static const String iconPremium = 'assets/images/icon_premium.svg';

  // Animations (Lottie)
  static const String lottieLoading = 'assets/animations/loading.json';
  static const String lottieSuccess = 'assets/animations/success.json';
  static const String lottieError = 'assets/animations/error.json';
  static const String lottieMagic = 'assets/animations/magic.json';
}
