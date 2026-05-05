import 'dart:io';
import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import 'package:uuid/uuid.dart';

/// Service pour l'animation de photos (style Harry Potter)
/// Utilise D-ID API pour créer des vidéos à partir de photos
class AnimationService {
  final Dio _dio;

  // D-ID API configuration
  static const String _baseUrl = 'https://api.d-id.com';
  static const String _apiKey = 'YOUR_D_ID_API_KEY'; // À configurer

  AnimationService() : _dio = Dio() {
    _dio.options.baseUrl = _baseUrl;
    _dio.options.headers = {
      'Authorization': 'Basic $_apiKey',
      'Content-Type': 'application/json',
    };
    _dio.options.connectTimeout = const Duration(seconds: 30);
    _dio.options.receiveTimeout = const Duration(seconds: 120);
  }

  /// Crée une animation à partir d'une photo
  /// Retourne l'ID de la tâche d'animation
  Future<String> createAnimation(String imagePath, {
    AnimationStyle style = AnimationStyle.subtle,
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
        throw AnimationException('Échec de la création: ${response.statusMessage}');
      }
    } on DioException catch (e) {
      throw AnimationException('Erreur réseau: ${e.message}');
    }
  }

  /// Vérifie le statut d'une animation
  Future<AnimationStatus> checkStatus(String animationId) async {
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

  /// Télécharge la vidéo animée
  Future<String> downloadAnimation(String resultUrl) async {
    try {
      final directory = await getApplicationDocumentsDirectory();
      final animatedDir = Directory('${directory.path}/animated');
      if (!await animatedDir.exists()) {
        await animatedDir.create(recursive: true);
      }

      final fileName = '${const Uuid().v4()}_animated.mp4';
      final filePath = '${animatedDir.path}/$fileName';

      await _dio.download(resultUrl, filePath);

      return filePath;
    } on DioException catch (e) {
      throw AnimationException('Échec du téléchargement: ${e.message}');
    }
  }

  /// Anime une photo et attend le résultat
  Future<String> animatePhoto(String imagePath, {
    AnimationStyle style = AnimationStyle.subtle,
    Duration timeout = const Duration(minutes: 2),
  }) async {
    // Créer l'animation
    final animationId = await createAnimation(imagePath, style: style);

    // Polling pour vérifier le statut
    final stopwatch = Stopwatch()..start();
    while (stopwatch.elapsed < timeout) {
      await Future.delayed(const Duration(seconds: 3));

      final status = await checkStatus(animationId);

      if (status.status == AnimationProcessStatus.done && status.resultUrl != null) {
        return await downloadAnimation(status.resultUrl!);
      } else if (status.status == AnimationProcessStatus.error) {
        throw AnimationException('L\'animation a échoué');
      }
    }

    throw AnimationException('Timeout: l\'animation a pris trop de temps');
  }

  /// Upload une image et retourne son URL
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
        return AnimationProcessStatus.processing;
      case 'done':
        return AnimationProcessStatus.done;
      case 'error':
        return AnimationProcessStatus.error;
      default:
        return AnimationProcessStatus.pending;
    }
  }
}

/// Provider pour le service d'animation
final animationServiceProvider = Provider<AnimationService>((ref) {
  return AnimationService();
});

/// Style d'animation
enum AnimationStyle {
  subtle,   // Mouvement subtil, léger
  moderate, // Mouvement modéré
  dynamic,  // Mouvement plus prononcé
}

/// Type de driver d'animation
enum AnimationDriver {
  natural,    // Mouvements naturels
  fun,        // Mouvements amusants
  expressive, // Mouvements expressifs
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
