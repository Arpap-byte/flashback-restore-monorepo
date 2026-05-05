import 'package:freezed_annotation/freezed_annotation.dart';

part 'purchase_model.freezed.dart';
part 'purchase_model.g.dart';

/// Modèle représentant un produit d'achat in-app
@freezed
class PurchaseProduct with _$PurchaseProduct {
  const factory PurchaseProduct({
    required String id,
    required String title,
    required String description,
    required String price,
    required ProductType type,
    int? credits, // Pour les packs de crédits
    String? periodUnit, // Pour les abonnements (month, year)
  }) = _PurchaseProduct;

  factory PurchaseProduct.fromJson(Map<String, dynamic> json) =>
      _$PurchaseProductFromJson(json);
}

/// Type de produit
enum ProductType {
  consumable, // Pack de crédits d'animation
  subscription, // Abonnement premium
}

/// Modèle représentant un achat effectué
@freezed
class PurchaseRecord with _$PurchaseRecord {
  const factory PurchaseRecord({
    required String id,
    required String productId,
    required String userId,
    required DateTime purchaseDate,
    required double amount,
    required String currency,
    required PurchaseStatus status,
    String? transactionId,
    String? receipt,
  }) = _PurchaseRecord;

  factory PurchaseRecord.fromJson(Map<String, dynamic> json) =>
      _$PurchaseRecordFromJson(json);
}

/// Statut d'un achat
enum PurchaseStatus {
  pending,
  completed,
  failed,
  refunded,
  cancelled,
}

/// Liste des produits disponibles
class AvailableProducts {
  AvailableProducts._();

  static const List<PurchaseProduct> animationPacks = [
    PurchaseProduct(
      id: 'animation_single',
      title: '1 Animation',
      description: 'Animez une photo',
      price: '1,99 €',
      type: ProductType.consumable,
      credits: 1,
    ),
    PurchaseProduct(
      id: 'animation_pack_5',
      title: '5 Animations',
      description: 'Pack de 5 animations - Économisez 20%',
      price: '7,99 €',
      type: ProductType.consumable,
      credits: 5,
    ),
    PurchaseProduct(
      id: 'animation_pack_10',
      title: '10 Animations',
      description: 'Pack de 10 animations - Économisez 35%',
      price: '12,99 €',
      type: ProductType.consumable,
      credits: 10,
    ),
  ];

  static const List<PurchaseProduct> subscriptions = [
    PurchaseProduct(
      id: 'premium_monthly',
      title: 'Premium Mensuel',
      description: 'Restaurations illimitées + Animations illimitées',
      price: '4,99 €',
      type: ProductType.subscription,
      periodUnit: 'month',
    ),
    PurchaseProduct(
      id: 'premium_yearly',
      title: 'Premium Annuel',
      description: 'Restaurations illimitées + Animations illimitées - 2 mois offerts',
      price: '39,99 €',
      type: ProductType.subscription,
      periodUnit: 'year',
    ),
  ];
}
