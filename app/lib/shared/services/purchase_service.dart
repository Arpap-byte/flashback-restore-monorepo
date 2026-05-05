import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:purchases_flutter/purchases_flutter.dart';

import '../models/purchase_model.dart';
import '../../core/constants/app_constants.dart';

/// Service pour la gestion des achats in-app via RevenueCat
class PurchaseService {
  static bool _isInitialized = false;

  /// Initialise RevenueCat
  static Future<void> initialize() async {
    if (_isInitialized) return;

    try {
      await Purchases.setLogLevel(LogLevel.debug);

      PurchasesConfiguration configuration;
      if (Platform.isAndroid) {
        configuration = PurchasesConfiguration(AppConstants.rcApiKeyAndroid);
      } else if (Platform.isIOS) {
        configuration = PurchasesConfiguration(AppConstants.rcApiKeyIOS);
      } else {
        throw UnsupportedError('Platform not supported');
      }

      await Purchases.configure(configuration);
      _isInitialized = true;

      debugPrint('RevenueCat initialized successfully');
    } catch (e) {
      debugPrint('Failed to initialize RevenueCat: $e');
    }
  }

  /// Récupère les offres disponibles
  Future<List<Package>> getOfferings() async {
    try {
      final offerings = await Purchases.getOfferings();

      if (offerings.current != null) {
        return offerings.current!.availablePackages;
      }

      return [];
    } catch (e) {
      debugPrint('Error fetching offerings: $e');
      return [];
    }
  }

  /// Récupère les informations client
  Future<CustomerInfo> getCustomerInfo() async {
    return await Purchases.getCustomerInfo();
  }

  /// Vérifie si l'utilisateur est premium
  Future<bool> isPremium() async {
    try {
      final customerInfo = await Purchases.getCustomerInfo();
      return customerInfo.entitlements.active.containsKey('premium');
    } catch (e) {
      debugPrint('Error checking premium status: $e');
      return false;
    }
  }

  /// Récupère le nombre de crédits d'animation
  Future<int> getAnimationCredits() async {
    try {
      final customerInfo = await Purchases.getCustomerInfo();
      // Les crédits sont stockés dans les attributs subscriber
      final credits = customerInfo.nonSubscriptionTransactions
          .where((t) => t.productIdentifier.contains('animation'))
          .length;
      return credits;
    } catch (e) {
      debugPrint('Error fetching animation credits: $e');
      return 0;
    }
  }

  /// Achète un package
  Future<PurchaseResult> purchase(Package package) async {
    try {
      final result = await Purchases.purchasePackage(package);

      return PurchaseResult(
        success: true,
        customerInfo: result,
        message: 'Achat réussi !',
      );
    } on PurchasesErrorCode catch (e) {
      String message;
      switch (e) {
        case PurchasesErrorCode.purchaseCancelledError:
          message = 'Achat annulé';
          break;
        case PurchasesErrorCode.purchaseNotAllowedError:
          message = 'Achats non autorisés sur cet appareil';
          break;
        case PurchasesErrorCode.purchaseInvalidError:
          message = 'Achat invalide';
          break;
        case PurchasesErrorCode.productNotAvailableForPurchaseError:
          message = 'Produit non disponible';
          break;
        case PurchasesErrorCode.networkError:
          message = 'Erreur réseau. Vérifiez votre connexion.';
          break;
        default:
          message = 'Une erreur est survenue';
      }

      return PurchaseResult(
        success: false,
        message: message,
      );
    } catch (e) {
      return PurchaseResult(
        success: false,
        message: 'Erreur: $e',
      );
    }
  }

  /// Achète un pack d'animations
  Future<PurchaseResult> purchaseAnimationPack(String productId) async {
    try {
      final offerings = await Purchases.getOfferings();
      final package = offerings.all.values
          .expand((o) => o.availablePackages)
          .firstWhere(
            (p) => p.storeProduct.identifier == productId,
            orElse: () => throw Exception('Produit non trouvé'),
          );

      return await purchase(package);
    } catch (e) {
      return PurchaseResult(
        success: false,
        message: 'Produit non trouvé: $e',
      );
    }
  }

  /// Souscrit à un abonnement premium
  Future<PurchaseResult> subscribePremium({bool yearly = false}) async {
    try {
      final offerings = await Purchases.getOfferings();
      final productId = yearly
          ? AppConstants.productPremiumYearly
          : AppConstants.productPremiumMonthly;

      final package = offerings.current?.availablePackages.firstWhere(
        (p) => p.storeProduct.identifier == productId,
        orElse: () => throw Exception('Abonnement non trouvé'),
      );

      if (package != null) {
        return await purchase(package);
      }

      return PurchaseResult(
        success: false,
        message: 'Abonnement non disponible',
      );
    } catch (e) {
      return PurchaseResult(
        success: false,
        message: 'Erreur: $e',
      );
    }
  }

  /// Restaure les achats
  Future<PurchaseResult> restorePurchases() async {
    try {
      final customerInfo = await Purchases.restorePurchases();

      final hasEntitlements = customerInfo.entitlements.active.isNotEmpty;

      return PurchaseResult(
        success: true,
        customerInfo: customerInfo,
        message: hasEntitlements
            ? 'Achats restaurés avec succès !'
            : 'Aucun achat à restaurer',
      );
    } catch (e) {
      return PurchaseResult(
        success: false,
        message: 'Erreur lors de la restauration: $e',
      );
    }
  }

  /// Identifie l'utilisateur (pour synchroniser les achats)
  Future<void> identifyUser(String userId) async {
    try {
      await Purchases.logIn(userId);
    } catch (e) {
      debugPrint('Error identifying user: $e');
    }
  }

  /// Déconnecte l'utilisateur
  Future<void> logoutUser() async {
    try {
      await Purchases.logOut();
    } catch (e) {
      debugPrint('Error logging out user: $e');
    }
  }
}

/// Provider pour le service d'achat
final purchaseServiceProvider = Provider<PurchaseService>((ref) {
  return PurchaseService();
});

/// Provider pour le statut premium
final isPremiumProvider = FutureProvider<bool>((ref) async {
  final service = ref.read(purchaseServiceProvider);
  return await service.isPremium();
});

/// Provider pour les crédits d'animation
final animationCreditsProvider = FutureProvider<int>((ref) async {
  final service = ref.read(purchaseServiceProvider);
  return await service.getAnimationCredits();
});

/// Résultat d'un achat
class PurchaseResult {
  final bool success;
  final String message;
  final CustomerInfo? customerInfo;

  PurchaseResult({
    required this.success,
    required this.message,
    this.customerInfo,
  });
}
