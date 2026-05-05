import 'dart:convert';
import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/photo_model.dart';
import '../../core/constants/app_constants.dart';

/// Service de stockage local
class StorageService {
  static const String _photosBoxName = 'photos';
  static const String _settingsBoxName = 'settings';

  late Box<String> _photosBox;
  late Box<dynamic> _settingsBox;
  late SharedPreferences _prefs;

  bool _isInitialized = false;

  /// Initialise le service de stockage
  Future<void> initialize() async {
    if (_isInitialized) return;

    _photosBox = await Hive.openBox<String>(_photosBoxName);
    _settingsBox = await Hive.openBox(_settingsBoxName);
    _prefs = await SharedPreferences.getInstance();

    _isInitialized = true;
  }

  // ============ PHOTOS ============

  /// Sauvegarde une photo
  Future<void> savePhoto(PhotoModel photo) async {
    final json = jsonEncode(photo.toJson());
    await _photosBox.put(photo.id, json);
  }

  /// Récupère une photo par son ID
  Future<PhotoModel?> getPhoto(String id) async {
    final json = _photosBox.get(id);
    if (json == null) return null;

    return PhotoModel.fromJson(jsonDecode(json));
  }

  /// Récupère toutes les photos
  Future<List<PhotoModel>> getAllPhotos() async {
    final photos = <PhotoModel>[];

    for (final json in _photosBox.values) {
      try {
        photos.add(PhotoModel.fromJson(jsonDecode(json)));
      } catch (e) {
        // Ignore les entrées corrompues
      }
    }

    // Trier par date de création (plus récent en premier)
    photos.sort((a, b) => b.createdAt.compareTo(a.createdAt));

    return photos;
  }

  /// Supprime une photo
  Future<void> deletePhoto(String id) async {
    final photo = await getPhoto(id);
    if (photo == null) return;

    // Supprimer les fichiers associés
    await _deleteFileIfExists(photo.originalPath);
    if (photo.restoredPath != null) {
      await _deleteFileIfExists(photo.restoredPath!);
    }
    if (photo.animatedVideoPath != null) {
      await _deleteFileIfExists(photo.animatedVideoPath!);
    }
    if (photo.thumbnailPath != null) {
      await _deleteFileIfExists(photo.thumbnailPath!);
    }

    await _photosBox.delete(id);
  }

  /// Supprime un fichier s'il existe
  Future<void> _deleteFileIfExists(String path) async {
    final file = File(path);
    if (await file.exists()) {
      await file.delete();
    }
  }

  /// Récupère les photos restaurées
  Future<List<PhotoModel>> getRestoredPhotos() async {
    final allPhotos = await getAllPhotos();
    return allPhotos.where((p) => p.restoredPath != null).toList();
  }

  /// Récupère les photos animées
  Future<List<PhotoModel>> getAnimatedPhotos() async {
    final allPhotos = await getAllPhotos();
    return allPhotos.where((p) => p.isAnimated).toList();
  }

  // ============ SETTINGS ============

  /// Vérifie si l'onboarding est terminé
  bool get isOnboardingComplete =>
      _prefs.getBool(AppConstants.keyOnboardingComplete) ?? false;

  /// Marque l'onboarding comme terminé
  Future<void> setOnboardingComplete() async {
    await _prefs.setBool(AppConstants.keyOnboardingComplete, true);
  }

  /// Récupère le nombre de restaurations gratuites utilisées
  int get freeRestorationsUsed =>
      _prefs.getInt(AppConstants.keyFreeRestorationsUsed) ?? 0;

  /// Incrémente le nombre de restaurations gratuites utilisées
  Future<void> incrementFreeRestorations() async {
    final current = freeRestorationsUsed;
    await _prefs.setInt(AppConstants.keyFreeRestorationsUsed, current + 1);
  }

  /// Vérifie si des restaurations gratuites sont disponibles
  bool get hasFreeRestorationsAvailable =>
      freeRestorationsUsed < AppConstants.freeRestorationsLimit;

  /// Nombre de restaurations gratuites restantes
  int get freeRestorationsRemaining =>
      AppConstants.freeRestorationsLimit - freeRestorationsUsed;

  /// Récupère le mode sombre
  bool get isDarkMode => _prefs.getBool(AppConstants.keyDarkMode) ?? false;

  /// Définit le mode sombre
  Future<void> setDarkMode(bool value) async {
    await _prefs.setBool(AppConstants.keyDarkMode, value);
  }

  /// Récupère la langue
  String get language => _prefs.getString(AppConstants.keyLanguage) ?? 'fr';

  /// Définit la langue
  Future<void> setLanguage(String value) async {
    await _prefs.setString(AppConstants.keyLanguage, value);
  }

  // ============ FILE MANAGEMENT ============

  /// Récupère le répertoire des photos originales
  Future<Directory> getOriginalsDirectory() async {
    final appDir = await getApplicationDocumentsDirectory();
    final dir = Directory('${appDir.path}/originals');
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }
    return dir;
  }

  /// Récupère le répertoire des photos restaurées
  Future<Directory> getRestoredDirectory() async {
    final appDir = await getApplicationDocumentsDirectory();
    final dir = Directory('${appDir.path}/restored');
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }
    return dir;
  }

  /// Récupère le répertoire des vidéos animées
  Future<Directory> getAnimatedDirectory() async {
    final appDir = await getApplicationDocumentsDirectory();
    final dir = Directory('${appDir.path}/animated');
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }
    return dir;
  }

  /// Récupère le répertoire des miniatures
  Future<Directory> getThumbnailsDirectory() async {
    final appDir = await getApplicationDocumentsDirectory();
    final dir = Directory('${appDir.path}/thumbnails');
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }
    return dir;
  }

  /// Calcule l'espace utilisé par l'application
  Future<int> getUsedStorageBytes() async {
    int totalSize = 0;

    final directories = [
      await getOriginalsDirectory(),
      await getRestoredDirectory(),
      await getAnimatedDirectory(),
      await getThumbnailsDirectory(),
    ];

    for (final dir in directories) {
      if (await dir.exists()) {
        await for (final entity in dir.list(recursive: true)) {
          if (entity is File) {
            totalSize += await entity.length();
          }
        }
      }
    }

    return totalSize;
  }

  /// Formate la taille en string lisible
  String formatStorageSize(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    if (bytes < 1024 * 1024 * 1024) {
      return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
    }
    return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(1)} GB';
  }

  /// Efface toutes les données
  Future<void> clearAllData() async {
    await _photosBox.clear();
    await _settingsBox.clear();

    // Supprimer les fichiers
    final directories = [
      await getOriginalsDirectory(),
      await getRestoredDirectory(),
      await getAnimatedDirectory(),
      await getThumbnailsDirectory(),
    ];

    for (final dir in directories) {
      if (await dir.exists()) {
        await dir.delete(recursive: true);
        await dir.create();
      }
    }
  }
}

/// Provider pour le service de stockage
final storageServiceProvider = Provider<StorageService>((ref) {
  return StorageService();
});

/// Provider pour initialiser le stockage
final storageInitProvider = FutureProvider<void>((ref) async {
  final service = ref.read(storageServiceProvider);
  await service.initialize();
});
