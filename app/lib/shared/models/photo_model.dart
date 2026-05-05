import 'package:freezed_annotation/freezed_annotation.dart';

part 'photo_model.freezed.dart';
part 'photo_model.g.dart';

/// Modèle représentant une photo dans l'application
@freezed
class PhotoModel with _$PhotoModel {
  const factory PhotoModel({
    required String id,
    required String originalPath,
    String? restoredPath,
    String? animatedVideoPath,
    required DateTime createdAt,
    DateTime? restoredAt,
    DateTime? animatedAt,
    @Default(PhotoStatus.original) PhotoStatus status,
    @Default(false) bool isAnimated,
    String? thumbnailPath,
    Map<String, dynamic>? metadata,
  }) = _PhotoModel;

  factory PhotoModel.fromJson(Map<String, dynamic> json) =>
      _$PhotoModelFromJson(json);
}

/// Statut de la photo
enum PhotoStatus {
  original,
  restoring,
  restored,
  animating,
  animated,
  failed,
}

/// Extension pour les labels de statut
extension PhotoStatusExtension on PhotoStatus {
  String get label {
    switch (this) {
      case PhotoStatus.original:
        return 'Original';
      case PhotoStatus.restoring:
        return 'Restauration en cours...';
      case PhotoStatus.restored:
        return 'Restaurée';
      case PhotoStatus.animating:
        return 'Animation en cours...';
      case PhotoStatus.animated:
        return 'Animée';
      case PhotoStatus.failed:
        return 'Échec';
    }
  }

  bool get isProcessing =>
      this == PhotoStatus.restoring || this == PhotoStatus.animating;
}
