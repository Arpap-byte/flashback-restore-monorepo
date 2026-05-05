import 'package:freezed_annotation/freezed_annotation.dart';

part 'user_model.freezed.dart';
part 'user_model.g.dart';

/// Modèle représentant un utilisateur
@freezed
class UserModel with _$UserModel {
  const factory UserModel({
    required String id,
    String? email,
    String? displayName,
    String? photoUrl,
    required DateTime createdAt,
    @Default(0) int freeRestorationsUsed,
    @Default(0) int animationCredits,
    @Default(false) bool isPremium,
    DateTime? premiumExpiresAt,
    @Default(SubscriptionType.none) SubscriptionType subscriptionType,
  }) = _UserModel;

  factory UserModel.fromJson(Map<String, dynamic> json) =>
      _$UserModelFromJson(json);
}

/// Type d'abonnement
enum SubscriptionType {
  none,
  monthly,
  yearly,
}

/// Extension pour les fonctionnalités utilisateur
extension UserModelExtension on UserModel {
  /// Vérifie si l'utilisateur peut faire une restauration gratuite
  bool get canUseFreeeRestoration => freeRestorationsUsed < 3;

  /// Nombre de restaurations gratuites restantes
  int get freeRestorationsRemaining => 3 - freeRestorationsUsed;

  /// Vérifie si l'abonnement est actif
  bool get hasActiveSubscription {
    if (!isPremium) return false;
    if (premiumExpiresAt == null) return false;
    return premiumExpiresAt!.isAfter(DateTime.now());
  }

  /// Vérifie si l'utilisateur peut animer une photo
  bool get canAnimate => hasActiveSubscription || animationCredits > 0;
}
