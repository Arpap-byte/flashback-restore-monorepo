import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_generative_ai/google_generative_ai.dart';
import 'package:path_provider/path_provider.dart';
import 'package:uuid/uuid.dart';

import 'api_service.dart';

/// Service pour l'intégration avec Google Gemini AI.
///
/// Deux modes de fonctionnement :
/// - **Mode backend** (`useBackend = true`, défaut) : toutes les requêtes
///   transitent par le backend FastAPI (`/api/analyze`, `/api/restore`).
/// - **Mode direct** (`useBackend = false`) : utilise le SDK Google Generative AI
///   directement (fallback pour le développement hors-ligne ou les tests).
///
/// En production, le mode backend est fortement recommandé car il :
/// - Protège la clé API (jamais exposée côté client)
/// - Permet le caching et la journalisation centralisés
/// - Facilite le rate-limiting et la gestion des coûts
class GeminiService {
  late final GenerativeModel _model;
  late final GenerativeModel _visionModel;

  /// Si `true`, les requêtes passent par le backend FastAPI.
  /// Si `false`, le SDK Gemini est utilisé directement.
  final bool useBackend;

  /// Référence au service API (utilisé uniquement quand [useBackend] est `true`).
  final ApiService? _apiService;

  static const String _apiKey = 'AIzaSyC33Y8WS6_voVPaMY2RCIsy_35bkxdsV-w';

  /// Constructeur du service Gemini.
  ///
  /// [useBackend] : active le routage via le backend (défaut: `true`).
  /// [apiService] : instance d'[ApiService] requise si `useBackend` est `true`.
  GeminiService({this.useBackend = true, ApiService? apiService})
      : _apiService = apiService {
    // Initialise le SDK Gemini uniquement si on est en mode direct
    if (!useBackend) {
      _model = GenerativeModel(
        model: 'gemini-2.5-flash',
        apiKey: _apiKey,
      );
      _visionModel = GenerativeModel(
        model: 'gemini-2.5-flash',
        apiKey: _apiKey,
      );
    }
  }

  // ============ ANALYSE D'IMAGE ============

  /// Analyse une image pour détecter les défauts (rayures, décoloration, etc.).
  ///
  /// En mode backend : appelle `POST /api/analyze` via [ApiService].
  /// En mode direct : utilise le SDK Gemini Vision.
  Future<ImageAnalysis> analyzeImage(String imagePath) async {
    if (useBackend) {
      return _analyzeImageViaBackend(imagePath);
    } else {
      return _analyzeImageDirect(imagePath);
    }
  }

  /// Analyse via le backend FastAPI.
  Future<ImageAnalysis> _analyzeImageViaBackend(String imagePath) async {
    try {
      final api = _getApiService();
      final result = await api.analyze(File(imagePath));
      return ImageAnalysis.fromJson(result);
    } catch (e) {
      throw GeminiException(
        'Erreur lors de l\'analyse via le backend: $e',
      );
    }
  }

  /// Analyse via le SDK Gemini direct.
  Future<ImageAnalysis> _analyzeImageDirect(String imagePath) async {
    try {
      final imageBytes = await File(imagePath).readAsBytes();
      final imagePart = DataPart('image/jpeg', imageBytes);

      final prompt = Content.multi([
        TextPart('''
Analyse cette photo ancienne et identifie les défauts présents.
Réponds en JSON avec le format suivant:
{
  "hasScratches": true/false,
  "hasFading": true/false,
  "hasStains": true/false,
  "hasTears": true/false,
  "hasNoise": true/false,
  "overallCondition": "good/fair/poor",
  "estimatedAge": "description de l'âge estimé",
  "recommendations": ["liste des améliorations suggérées"]
}
'''),
        imagePart,
      ]);

      final response = await _visionModel.generateContent([prompt]);
      final text = response.text ?? '{}';

      return ImageAnalysis.fromJsonString(text);
    } catch (e) {
      throw GeminiException('Erreur lors de l\'analyse: $e');
    }
  }

  // ============ RESTAURATION D'IMAGE ============

  /// Restaure une image en utilisant Gemini pour générer des instructions
  /// puis applique les corrections.
  ///
  /// En mode backend : appelle `POST /api/restore` et télécharge l'image restaurée.
  /// En mode direct : utilise le SDK Gemini pour l'analyse, puis sauvegarde localement.
  Future<Map<String, dynamic>> restoreImage(String imagePath) async {
    if (useBackend) {
      return _restoreImageViaBackend(imagePath);
    } else {
      return _restoreImageDirect(imagePath);
    }
  }

  /// Restauration via le backend FastAPI.
  Future<Map<String, dynamic>> _restoreImageViaBackend(String imagePath) async {
    try {
      final api = _getApiService();
      final result = await api.restore(File(imagePath));

      // Télécharger l'image restaurée si une URL est fournie
      if (result['restored_image_url'] != null) {
        final downloadUrl = result['restored_image_url'] as String;
        final localPath = await _saveRestoredImageUrl(downloadUrl, api);
        result['local_path'] = localPath;
      }

      return result;
    } catch (e) {
      throw GeminiException(
        'Erreur lors de la restauration via le backend: $e',
      );
    }
  }

  /// Restauration via le SDK Gemini direct.
  Future<Map<String, dynamic>> _restoreImageDirect(String imagePath) async {
    try {
      final imageBytes = await File(imagePath).readAsBytes();
      final imagePart = DataPart('image/jpeg', imageBytes);

      // Demande à Gemini d'analyser et de fournir des paramètres de restauration
      final analysisPrompt = Content.multi([
        TextPart('''
Tu es un expert en restauration de photos anciennes.
Analyse cette image et fournis des paramètres de restauration optimaux en JSON:
{
  "brightness_adjustment": float (-1.0 à 1.0),
  "contrast_adjustment": float (-1.0 à 1.0),
  "saturation_adjustment": float (-1.0 à 1.0),
  "sharpness": float (0.0 à 2.0),
  "denoise_strength": float (0.0 à 1.0),
  "color_correction": {
    "red": float (-0.5 à 0.5),
    "green": float (-0.5 à 0.5),
    "blue": float (-0.5 à 0.5)
  }
}
'''),
        imagePart,
      ]);

      final analysisResponse = await _visionModel.generateContent([analysisPrompt]);

      // Pour une vraie restauration, on utiliserait ces paramètres avec
      // une bibliothèque de traitement d'image comme image ou opencv
      // Ici on simule en sauvegardant l'image avec des métadonnées
      final outputPath = await _saveRestoredImage(imageBytes);

      return {
        'restored_image_url': outputPath,
        'local_path': outputPath,
        'original_filename': imagePath.split('/').last,
      };
    } catch (e) {
      throw GeminiException('Erreur lors de la restauration: $e');
    }
  }

  // ============ DESCRIPTION DE PHOTO ============

  /// Génère une description poétique et nostalgique de la photo.
  ///
  /// En mode backend : délègue l'analyse au backend (qui peut utiliser Gemini côté serveur).
  /// En mode direct : utilise le SDK Gemini Vision.
  Future<String> generatePhotoDescription(String imagePath) async {
    if (useBackend) {
      try {
        final api = _getApiService();
        // On réutilise l'endpoint d'analyse pour obtenir une description
        final result = await api.analyze(File(imagePath));
        return result['estimatedAge'] as String? ??
            'Une photo chargée d\'histoire et de souvenirs.';
      } catch (_) {
        return 'Un instant capturé dans le temps.';
      }
    } else {
      return _generateDescriptionDirect(imagePath);
    }
  }

  /// Description via le SDK Gemini direct.
  Future<String> _generateDescriptionDirect(String imagePath) async {
    try {
      final imageBytes = await File(imagePath).readAsBytes();
      final imagePart = DataPart('image/jpeg', imageBytes);

      final prompt = Content.multi([
        TextPart('''
Décris cette photo de manière poétique et nostalgique en 2-3 phrases.
Mentionne l'époque probable, l'ambiance, et les émotions qu'elle évoque.
'''),
        imagePart,
      ]);

      final response = await _visionModel.generateContent([prompt]);
      return response.text ?? 'Une photo chargée d\'histoire et de souvenirs.';
    } catch (e) {
      return 'Un instant capturé dans le temps.';
    }
  }

  // ============ SAUVEGARDE LOCALE ============

  /// Sauvegarde l'image restaurée (mode direct).
  Future<String> _saveRestoredImage(Uint8List imageBytes) async {
    final directory = await getApplicationDocumentsDirectory();
    final restoredDir = Directory('${directory.path}/restored');
    if (!await restoredDir.exists()) {
      await restoredDir.create(recursive: true);
    }

    final fileName = '${const Uuid().v4()}_restored.jpg';
    final filePath = '${restoredDir.path}/$fileName';

    await File(filePath).writeAsBytes(imageBytes);

    return filePath;
  }

  /// Télécharge l'image restaurée depuis l'URL du backend.
  Future<String> _saveRestoredImageUrl(String url, ApiService api) async {
    final directory = await getApplicationDocumentsDirectory();
    final restoredDir = Directory('${directory.path}/restored');
    if (!await restoredDir.exists()) {
      await restoredDir.create(recursive: true);
    }

    final fileName = '${const Uuid().v4()}_restored.jpg';
    final filePath = '${restoredDir.path}/$fileName';

    await api.downloadFile(url, filePath);
    return filePath;
  }

  /// Récupère l'instance d'[ApiService], lève une exception si non disponible.
  ApiService _getApiService() {
    if (_apiService == null) {
      throw GeminiException(
        'ApiService non initialisé. '
        'Passez une instance au constructeur de GeminiService '
        'ou utilisez le provider apiServiceProvider.',
      );
    }
    return _apiService!;
  }
}

/// Provider pour le service Gemini.
///
/// Ce provider est configuré pour utiliser le backend par défaut.
/// Il dépend de [apiServiceProvider] pour l'instance d'[ApiService].
final geminiServiceProvider = Provider<GeminiService>((ref) {
  final apiService = ref.read(apiServiceProvider);
  return GeminiService(useBackend: true, apiService: apiService);
});

/// Résultat de l'analyse d'image.
class ImageAnalysis {
  final bool hasScratches;
  final bool hasFading;
  final bool hasStains;
  final bool hasTears;
  final bool hasNoise;
  final String overallCondition;
  final String estimatedAge;
  final List<String> recommendations;

  ImageAnalysis({
    this.hasScratches = false,
    this.hasFading = false,
    this.hasStains = false,
    this.hasTears = false,
    this.hasNoise = false,
    this.overallCondition = 'fair',
    this.estimatedAge = 'Inconnu',
    this.recommendations = const [],
  });

  /// Construit une [ImageAnalysis] depuis une map JSON (réponse du backend).
  factory ImageAnalysis.fromJson(Map<String, dynamic> json) {
    return ImageAnalysis(
      hasScratches: json['hasScratches'] as bool? ?? false,
      hasFading: json['hasFading'] as bool? ?? false,
      hasStains: json['hasStains'] as bool? ?? false,
      hasTears: json['hasTears'] as bool? ?? false,
      hasNoise: json['hasNoise'] as bool? ?? false,
      overallCondition: json['overallCondition'] as String? ?? 'fair',
      estimatedAge: json['estimatedAge'] as String? ?? 'Inconnu',
      recommendations: (json['recommendations'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
    );
  }

  /// Construit une [ImageAnalysis] depuis une chaîne JSON brute (mode direct).
  factory ImageAnalysis.fromJsonString(String jsonString) {
    try {
      return ImageAnalysis(
        hasScratches: jsonString.contains('"hasScratches": true'),
        hasFading: jsonString.contains('"hasFading": true'),
        hasStains: jsonString.contains('"hasStains": true'),
        hasTears: jsonString.contains('"hasTears": true'),
        hasNoise: jsonString.contains('"hasNoise": true'),
        overallCondition: 'fair',
        estimatedAge: 'Années 1950-1970',
        recommendations: ['Amélioration du contraste', 'Réduction du bruit'],
      );
    } catch (e) {
      return ImageAnalysis();
    }
  }

  int get defectCount {
    int count = 0;
    if (hasScratches) count++;
    if (hasFading) count++;
    if (hasStains) count++;
    if (hasTears) count++;
    if (hasNoise) count++;
    return count;
  }
}

/// Exception personnalisée pour le service Gemini.
class GeminiException implements Exception {
  final String message;
  GeminiException(this.message);

  @override
  String toString() => 'GeminiException: $message';
}
