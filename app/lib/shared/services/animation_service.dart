import 'dart:io';
import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import 'package:uuid/uuid.dart';

import 'api_service.dart';

/// Service pour l'animation de photos (style Harry Potter).
///
/// Deux modes de fonctionnement :
/// - **Mode backend** (`useBackend = true`, défaut) : toutes les requêtes
///   transitent par le backend FastAPI (`/api/animate`, `/api/animate/{id}`).
/// - **Mode direct** (`useBackend = false`) : utilise l'API D-ID directement
///   (fallback pour le développement ou les tests).
///
/// En production, le mode backend est fortement recommandé car il :
/// - Protège la clé API D-ID (jamais exposée côté client)
/// - Permet la mise en cache et la journalisation
/// - Offre un point de contrôle unique pour le rate-limiting
class AnimationService {
  final Dio _dio;

  /// Si `true`, les requêtes passent par le backend FastAPI.
  /// Si `false`, l'API D-ID est appelée directement.
  final bool useBackend;

  /// Référence au service API (utilisé uniquement quand [useBackend] est `true`).
  final ApiService? _apiService;

  // D-ID API configuration (utilisée uniquement en mode direct)
  static const String _baseUrl = 'https://api.d-id.com';
  static const String _apiKey = 'YOUR_D_ID_API_KEY'; // À configurer

  /// Constructeur du service d'animation.
  ///
  /// [useBackend] : active le routage via le backend (défaut: `true`).
  /// [apiService] : instance d'[ApiService] requise si `useBackend` est `true`.
  AnimationService({this.useBackend = true, ApiService? apiService})
      : _apiService = apiService,
        _dio = Dio() {
    if (!useBackend) {
      // Configuration D-ID directe
      _dio.options.baseUrl = _baseUrl;
      _dio.options.headers = {
        'Authorization': 'Basic $_apiKey',
        'Content-Type': 'application/json',
      };
      _dio.options.connectTimeout = const Duration(seconds: 30);
      _dio.options.receiveTimeout = const Duration(seconds: 120);
    }
  }

  // ============ CRÉATION D'ANIMATION ============

  /// Crée une animation à partir d'une photo.
  ///
  /// En mode backend : appelle `POST /api/animate` avec l'image et un texte.
  /// En mode direct : upload l'image sur D-ID puis crée l'animation.
  ///
  /// Retourne l'ID du job d'animation.
  Future<String> createAnimation(
    String imagePath, {
    AnimationStyle style = AnimationStyle.subtle,
    AnimationDriver driver = AnimationDriver.natural,
    String text = 'Bonjour, je suis un souvenir animé.',
  }) async {
    if (useBackend) {
      return _createAnimationViaBackend(imagePath, text);
    } else {
      return _createAnimationDirect(imagePath, driver: driver);
    }
  }

  /// Création d'animation via le backend FastAPI.
  Future<String> _createAnimationViaBackend(
    String imagePath,
    String text,
  ) async {
    try {
      final api = _getApiService();
      final result = await api.animate(File(imagePath), text);

      final jobId = result['job_id'] as String?;
      if (jobId == null || jobId.isEmpty) {
        throw AnimationException('Le backend n\'a pas retourné de job_id');
      }

      return jobId;
    } catch (e) {
      if (e is AnimationException) rethrow;
      throw AnimationException(
        'Erreur lors de la création d\'animation via le backend: $e',
      );
    }
  }

  /// Création d'animation via l'API D-ID directe.
  Future<String> _createAnimationDirect(
    String imagePath, {
    AnimationDriver driver = AnimationDriver.natural,
  }) async {
    try {
      // Upload de l'image
      final imageUrl = await _uploadImage(imagePath);

      // Création de l'animation
      final response = await _dio.post(
        '/animations',
        data: {
          'source_url': imageUrl,
          'driver_url': _getDriverUrl(driver),
          'config': {
            'stitch': true,
            'result_format': 'mp4',
          },
          'face': {
            'size': 512,
            'top_crop': 0,
            'bottom_crop': 0,
          },
        },
      );

      if (response.statusCode == 201) {
        return response.data['id'];
      } else {
        throw AnimationException(
          'Échec de la création: ${response.statusMessage}',
        );
      }
    } on DioException catch (e) {
      throw AnimationException('Erreur réseau: ${e.message}');
    }
  }

  // ============ VÉRIFICATION DU STATUT ============

  /// Vérifie le statut d'une animation.
  ///
  /// En mode backend : appelle `GET /api/animate/{animationId}`.
  /// En mode direct : appelle l'API D-ID `GET /animations/{animationId}`.
  Future<AnimationStatus> checkStatus(String animationId) async {
    if (useBackend) {
      return _checkStatusViaBackend(animationId);
    } else {
      return _checkStatusDirect(animationId);
    }
  }

  /// Vérification du statut via le backend FastAPI.
  Future<AnimationStatus> _checkStatusViaBackend(String animationId) async {
    try {
      final api = _getApiService();
      final result = await api.checkAnimationStatus(animationId);

      return AnimationStatus(
        id: result['job_id'] as String? ?? animationId,
        status: _parseStatus(result['status'] as String? ?? 'pending'),
        resultUrl: result['video_url'] as String?,
        progress: result['progress'] as int? ?? 0,
      );
    } catch (e) {
      throw AnimationException(
        'Erreur lors de la vérification du statut via le backend: $e',
      );
    }
  }

  /// Vérification du statut via l'API D-ID directe.
  Future<AnimationStatus> _checkStatusDirect(String animationId) async {
    try {
      final response = await _dio.get('/animations/$animationId');

      if (response.statusCode == 200) {
        final status = response.data['status'];
        final resultUrl = response.data['result_url'];

        return AnimationStatus(
          id: animationId,
          status: _parseStatus(status),
          resultUrl: resultUrl,
          progress: response.data['progress'] ?? 0,
        );
      } else {
        throw AnimationException('Échec de la vérification du statut');
      }
    } on DioException catch (e) {
      throw AnimationException('Erreur réseau: ${e.message}');
    }
  }

  // ============ TÉLÉCHARGEMENT ============

  /// Télécharge la vidéo animée.
  ///
  /// En mode backend : télécharge depuis l'URL fournie par le backend.
  /// En mode direct : télécharge depuis l'URL D-ID.
  Future<String> downloadAnimation(String resultUrl) async {
    try {
      final directory = await getApplicationDocumentsDirectory();
      final animatedDir = Directory('${directory.path}/animated');
      if (!await animatedDir.exists()) {
        await animatedDir.create(recursive: true);
      }

      final fileName = '${const Uuid().v4()}_animated.mp4';
      final filePath = '${animatedDir.path}/$fileName';

      if (useBackend) {
        final api = _getApiService();
        await api.downloadFile(resultUrl, filePath);
      } else {
        await _dio.download(resultUrl, filePath);
      }

      return filePath;
    } on DioException catch (e) {
      throw AnimationException('Échec du téléchargement: ${e.message}');
    }
  }

  // ============ FLUX COMPLET ============

  /// Anime une photo et attend le résultat (création + polling + téléchargement).
  Future<String> animatePhoto(
    String imagePath, {
    AnimationStyle style = AnimationStyle.subtle,
    Duration timeout = const Duration(minutes: 2),
    String text = 'Bonjour, je suis un souvenir animé.',
  }) async {
    // Créer l'animation
    final animationId = await createAnimation(
      imagePath,
      style: style,
      text: text,
    );

    // Polling pour vérifier le statut
    final stopwatch = Stopwatch()..start();
    while (stopwatch.elapsed < timeout) {
      await Future.delayed(const Duration(seconds: 3));

      final status = await checkStatus(animationId);

      if (status.status == AnimationProcessStatus.done &&
          status.resultUrl != null) {
        return await downloadAnimation(status.resultUrl!);
      } else if (status.status == AnimationProcessStatus.error) {
        throw AnimationException('L\'animation a échoué');
      }
    }

    throw AnimationException('Timeout: l\'animation a pris trop de temps');
  }

  // ============ UPLOAD D'IMAGE (MODE DIRECT UNIQUEMENT) ============

  /// Upload une image sur D-ID et retourne son URL (mode direct uniquement).
  Future<String> _uploadImage(String imagePath) async {
    final bytes = await File(imagePath).readAsBytes();
    final base64Image = base64Encode(bytes);

    final response = await _dio.post(
      '/images',
      data: {
        'image': 'data:image/jpeg;base64,$base64Image',
      },
    );

    if (response.statusCode == 201) {
      return response.data['url'];
    } else {
      throw AnimationException('Échec de l\'upload de l\'image');
    }
  }

  // ============ UTILITAIRES ============

  String _getDriverUrl(AnimationDriver driver) {
    switch (driver) {
      case AnimationDriver.natural:
        return 'bank://natural/driver-01';
      case AnimationDriver.fun:
        return 'bank://fun/driver-01';
      case AnimationDriver.expressive:
        return 'bank://expressive/driver-01';
    }
  }

  AnimationProcessStatus _parseStatus(String status) {
    switch (status.toLowerCase()) {
      case 'created':
      case 'started':
      case 'processing':
        return AnimationProcessStatus.processing;
      case 'done':
        return AnimationProcessStatus.done;
      case 'error':
        return AnimationProcessStatus.error;
      default:
        return AnimationProcessStatus.pending;
    }
  }

  /// Récupère l'instance d'[ApiService], lève une exception si non disponible.
  ApiService _getApiService() {
    if (_apiService == null) {
      throw AnimationException(
        'ApiService non initialisé. '
        'Passez une instance au constructeur de AnimationService '
        'ou utilisez le provider animationServiceProvider.',
      );
    }
    return _apiService!;
  }
}

/// Provider pour le service d'animation.
///
/// Ce provider est configuré pour utiliser le backend par défaut.
/// Il dépend de [apiServiceProvider] pour l'instance d'[ApiService].
final animationServiceProvider = Provider<AnimationService>((ref) {
  final apiService = ref.read(apiServiceProvider);
  return AnimationService(useBackend: true, apiService: apiService);
});

/// Style d'animation
enum AnimationStyle {
  subtle,    // Mouvement subtil, léger
  moderate,  // Mouvement modéré
  dynamic,   // Mouvement plus prononcé
}

/// Type de driver d'animation
enum AnimationDriver {
  natural,     // Mouvements naturels
  fun,         // Mouvements amusants
  expressive,  // Mouvements expressifs
}

/// Statut du processus d'animation
enum AnimationProcessStatus {
  pending,
  processing,
  done,
  error,
}

/// Statut d'une animation
class AnimationStatus {
  final String id;
  final AnimationProcessStatus status;
  final String? resultUrl;
  final int progress;

  AnimationStatus({
    required this.id,
    required this.status,
    this.resultUrl,
    this.progress = 0,
  });

  bool get isDone => status == AnimationProcessStatus.done;
  bool get hasError => status == AnimationProcessStatus.error;
  bool get isProcessing => status == AnimationProcessStatus.processing;
}

/// Exception personnalisée pour le service d'animation
class AnimationException implements Exception {
  final String message;
  AnimationException(this.message);

  @override
  String toString() => 'AnimationException: $message';
}
