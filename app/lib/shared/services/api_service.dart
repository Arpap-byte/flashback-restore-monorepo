import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/app_constants.dart';

/// Service API pour communiquer avec le backend FastAPI de Flashback Restore.
///
/// Toutes les requêtes d'IA (analyse, restauration, animation) transitent
/// par ce backend au lieu d'appeler directement les SDK tiers.
class ApiService {
  final Dio _dio;

  ApiService({String? baseUrl})
      : _dio = Dio(BaseOptions(
          baseUrl: baseUrl ?? AppConstants.apiBaseUrl,
          connectTimeout: AppConstants.apiTimeout,
          receiveTimeout: const Duration(seconds: 120),
          headers: {
            'Accept': 'application/json',
          },
        )) {
    _dio.interceptors.add(LogInterceptor(
      requestBody: false,
      responseBody: true,
      error: true,
    ));
  }

  // ============ HEALTH CHECK ============

  /// Vérifie que le backend est en ligne et opérationnel.
  ///
  /// Retourne `true` si le backend répond avec un statut 200.
  Future<bool> healthCheck() async {
    try {
      final response = await _dio.get('/api/health');
      return response.statusCode == 200;
    } on DioException {
      return false;
    }
  }

  // ============ ANALYSE D'IMAGE ============

  /// Analyse une photo pour détecter les défauts (rayures, décoloration, etc.).
  ///
  /// Envoie l'image au backend via POST /api/analyze en multipart/form-data.
  /// Retourne un [Map] contenant le JSON d'analyse des défauts.
  ///
  /// Le JSON retourné par le backend a le format :
  /// ```json
  /// {
  ///   "hasScratches": bool,
  ///   "hasFading": bool,
  ///   "hasStains": bool,
  ///   "hasTears": bool,
  ///   "hasNoise": bool,
  ///   "overallCondition": "good" | "fair" | "poor",
  ///   "estimatedAge": "string",
  ///   "recommendations": ["string", ...]
  /// }
  /// ```
  Future<Map<String, dynamic>> analyze(File image) async {
    try {
      final formData = FormData.fromMap({
        'image': await MultipartFile.fromFile(
          image.path,
          filename: image.path.split('/').last,
        ),
      });

      final response = await _dio.post('/api/analyze', data: formData);

      if (response.statusCode == 200) {
        return Map<String, dynamic>.from(response.data);
      } else {
        throw ApiException(
          'Échec de l\'analyse: ${response.statusMessage}',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw ApiException(
        'Erreur réseau lors de l\'analyse: ${e.message}',
        statusCode: e.response?.statusCode,
      );
    }
  }

  // ============ RESTAURATION D'IMAGE ============

  /// Restaure une photo ancienne en utilisant le backend IA.
  ///
  /// Envoie l'image au backend via POST /api/restore en multipart/form-data.
  /// Retourne un [Map] contenant l'URL de l'image restaurée et les métadonnées.
  ///
  /// Format de la réponse :
  /// ```json
  /// {
  ///   "restored_image_url": "string",
  ///   "original_filename": "string",
  ///   "processing_time_ms": int
  /// }
  /// ```
  Future<Map<String, dynamic>> restore(File image) async {
    try {
      final formData = FormData.fromMap({
        'image': await MultipartFile.fromFile(
          image.path,
          filename: image.path.split('/').last,
        ),
      });

      final response = await _dio.post('/api/restore', data: formData);

      if (response.statusCode == 200) {
        return Map<String, dynamic>.from(response.data);
      } else {
        throw ApiException(
          'Échec de la restauration: ${response.statusMessage}',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw ApiException(
        'Erreur réseau lors de la restauration: ${e.message}',
        statusCode: e.response?.statusCode,
      );
    }
  }

  // ============ ANIMATION DE PHOTO ============

  /// Crée une animation à partir d'une photo et d'un texte.
  ///
  /// Envoie l'image et le texte au backend via POST /api/animate
  /// en multipart/form-data. Retourne un [Map] contenant l'ID du job D-ID.
  ///
  /// Format de la réponse :
  /// ```json
  /// {
  ///   "job_id": "string",
  ///   "status": "string"
  /// }
  /// ```
  Future<Map<String, dynamic>> animate(File image, String text) async {
    try {
      final formData = FormData.fromMap({
        'image': await MultipartFile.fromFile(
          image.path,
          filename: image.path.split('/').last,
        ),
        'text': text,
      });

      final response = await _dio.post('/api/animate', data: formData);

      if (response.statusCode == 200) {
        return Map<String, dynamic>.from(response.data);
      } else {
        throw ApiException(
          'Échec de l\'animation: ${response.statusMessage}',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw ApiException(
        'Erreur réseau lors de l\'animation: ${e.message}',
        statusCode: e.response?.statusCode,
      );
    }
  }

  // ============ STATUT D'ANIMATION ============

  /// Vérifie le statut d'un job d'animation D-ID via le backend.
  ///
  /// Appelle GET /api/animate/{jobId} et retourne le statut actuel
  /// ainsi que l'URL de la vidéo si l'animation est terminée.
  ///
  /// Format de la réponse :
  /// ```json
  /// {
  ///   "job_id": "string",
  ///   "status": "pending" | "processing" | "done" | "error",
  ///   "video_url": "string | null",
  ///   "progress": int
  /// }
  /// ```
  Future<Map<String, dynamic>> checkAnimationStatus(String jobId) async {
    try {
      final response = await _dio.get('/api/animate/$jobId');

      if (response.statusCode == 200) {
        return Map<String, dynamic>.from(response.data);
      } else {
        throw ApiException(
          'Échec de la vérification du statut: ${response.statusMessage}',
          statusCode: response.statusCode,
        );
      }
    } on DioException catch (e) {
      throw ApiException(
        'Erreur réseau lors de la vérification du statut: ${e.message}',
        statusCode: e.response?.statusCode,
      );
    }
  }

  // ============ UTILITAIRES ============

  /// Télécharge un fichier depuis une URL distante et le sauvegarde localement.
  ///
  /// Retourne le chemin du fichier local téléchargé.
  Future<String> downloadFile(String url, String savePath) async {
    try {
      await _dio.download(url, savePath);
      return savePath;
    } on DioException catch (e) {
      throw ApiException(
        'Échec du téléchargement: ${e.message}',
        statusCode: e.response?.statusCode,
      );
    }
  }

  /// Met à jour l'URL de base du backend (utile pour le changement d'environnement).
  void setBaseUrl(String baseUrl) {
    _dio.options.baseUrl = baseUrl;
  }
}

// ============ PROVIDERS ============

/// Provider pour le service API (singleton).
final apiServiceProvider = Provider<ApiService>((ref) {
  return ApiService();
});

/// Provider pour vérifier l'état du backend au démarrage.
final backendHealthProvider = FutureProvider<bool>((ref) async {
  final apiService = ref.read(apiServiceProvider);
  return await apiService.healthCheck();
});

// ============ EXCEPTIONS ============

/// Exception personnalisée pour les erreurs de l'API backend.
class ApiException implements Exception {
  /// Message d'erreur lisible.
  final String message;

  /// Code de statut HTTP (peut être null si l'erreur est locale).
  final int? statusCode;

  const ApiException(this.message, {this.statusCode});

  @override
  String toString() => 'ApiException($statusCode): $message';
}
