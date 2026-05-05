import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:uuid/uuid.dart';

import '../../../../core/constants/app_constants.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../shared/models/photo_model.dart';
import '../../../../shared/services/gemini_service.dart';
import '../../../../shared/services/storage_service.dart';

class RestorationScreen extends ConsumerStatefulWidget {
  const RestorationScreen({super.key});

  @override
  ConsumerState<RestorationScreen> createState() => _RestorationScreenState();
}

class _RestorationScreenState extends ConsumerState<RestorationScreen> {
  final ImagePicker _imagePicker = ImagePicker();
  String? _selectedImagePath;
  bool _isAnalyzing = false;
  bool _isRestoring = false;
  ImageAnalysis? _analysis;
  String? _errorMessage;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.backgroundLight,
      appBar: AppBar(
        title: const Text('Restaurer une photo'),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => context.pop(),
        ),
      ),
      body: _selectedImagePath == null
          ? _buildImageSelector()
          : _buildRestorationView(),
    );
  }

  Widget _buildImageSelector() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 120,
              height: 120,
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.1),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.add_photo_alternate_outlined,
                size: 60,
                color: AppColors.primary,
              ),
            ).animate().scale(duration: 500.ms, curve: Curves.elasticOut),
            const SizedBox(height: 32),
            Text(
              'Sélectionnez une photo',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 12),
            Text(
              'Choisissez une photo ancienne ou abîmée à restaurer',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.textSecondary,
                  ),
            ),
            const SizedBox(height: 48),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _SelectionButton(
                  icon: Icons.photo_library_outlined,
                  label: 'Galerie',
                  onTap: _pickFromGallery,
                ),
                const SizedBox(width: 24),
                _SelectionButton(
                  icon: Icons.camera_alt_outlined,
                  label: 'Caméra',
                  onTap: _takePhoto,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRestorationView() {
    return SingleChildScrollView(
      child: Column(
        children: [
          // Image preview
          Container(
            width: double.infinity,
            height: 350,
            margin: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(20),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.1),
                  blurRadius: 20,
                  offset: const Offset(0, 10),
                ),
              ],
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(20),
              child: Stack(
                fit: StackFit.expand,
                children: [
                  Image.file(
                    File(_selectedImagePath!),
                    fit: BoxFit.cover,
                  ),
                  if (_isAnalyzing || _isRestoring)
                    Container(
                      color: Colors.black.withOpacity(0.5),
                      child: Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const CircularProgressIndicator(
                              color: Colors.white,
                            ),
                            const SizedBox(height: 16),
                            Text(
                              _isAnalyzing
                                  ? 'Analyse en cours...'
                                  : 'Restauration en cours...',
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 16,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ).animate().fadeIn(duration: 400.ms).slideY(begin: 0.1, end: 0),

          // Analysis results
          if (_analysis != null) _buildAnalysisResults(),

          // Error message
          if (_errorMessage != null)
            Container(
              margin: const EdgeInsets.all(16),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.error.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  const Icon(Icons.error_outline, color: AppColors.error),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      _errorMessage!,
                      style: const TextStyle(color: AppColors.error),
                    ),
                  ),
                ],
              ),
            ),

          // Actions
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                if (!_isAnalyzing && !_isRestoring && _analysis == null)
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _analyzeImage,
                      icon: const Icon(Icons.search),
                      label: const Text('Analyser la photo'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.secondary,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                    ),
                  ),
                if (_analysis != null && !_isRestoring) ...[
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _restoreImage,
                      icon: const Icon(Icons.auto_fix_high),
                      label: const Text('Restaurer maintenant'),
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                ],
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: _changeImage,
                    icon: const Icon(Icons.refresh),
                    label: const Text('Changer de photo'),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAnalysisResults() {
    final analysis = _analysis!;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surfaceLight,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.analytics_outlined, color: AppColors.primary),
              const SizedBox(width: 12),
              Text(
                'Résultat de l\'analyse',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          _buildConditionBadge(analysis.overallCondition),
          const SizedBox(height: 16),
          Text(
            'Défauts détectés (${analysis.defectCount})',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              if (analysis.hasScratches)
                _DefectChip(label: 'Rayures', icon: Icons.auto_fix_off),
              if (analysis.hasFading)
                _DefectChip(label: 'Décoloration', icon: Icons.wb_sunny_outlined),
              if (analysis.hasStains)
                _DefectChip(label: 'Taches', icon: Icons.water_drop_outlined),
              if (analysis.hasTears)
                _DefectChip(label: 'Déchirures', icon: Icons.broken_image_outlined),
              if (analysis.hasNoise)
                _DefectChip(label: 'Bruit', icon: Icons.grain),
            ],
          ),
          if (analysis.recommendations.isNotEmpty) ...[
            const SizedBox(height: 16),
            const Divider(),
            const SizedBox(height: 12),
            Text(
              'Recommandations',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
            const SizedBox(height: 8),
            ...analysis.recommendations.map(
              (r) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  children: [
                    const Icon(
                      Icons.check_circle,
                      size: 16,
                      color: AppColors.success,
                    ),
                    const SizedBox(width: 8),
                    Expanded(child: Text(r)),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    ).animate().fadeIn(duration: 400.ms).slideY(begin: 0.1, end: 0);
  }

  Widget _buildConditionBadge(String condition) {
    Color color;
    String label;
    IconData icon;

    switch (condition.toLowerCase()) {
      case 'good':
        color = AppColors.success;
        label = 'Bon état';
        icon = Icons.check_circle;
        break;
      case 'fair':
        color = AppColors.warning;
        label = 'État moyen';
        icon = Icons.warning;
        break;
      case 'poor':
        color = AppColors.error;
        label = 'Mauvais état';
        icon = Icons.error;
        break;
      default:
        color = AppColors.info;
        label = 'Inconnu';
        icon = Icons.help;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 18, color: color),
          const SizedBox(width: 8),
          Text(
            label,
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _pickFromGallery() async {
    final XFile? image = await _imagePicker.pickImage(
      source: ImageSource.gallery,
      maxWidth: 2048,
      maxHeight: 2048,
      imageQuality: 90,
    );

    if (image != null) {
      setState(() {
        _selectedImagePath = image.path;
        _analysis = null;
        _errorMessage = null;
      });
    }
  }

  Future<void> _takePhoto() async {
    final XFile? image = await _imagePicker.pickImage(
      source: ImageSource.camera,
      maxWidth: 2048,
      maxHeight: 2048,
      imageQuality: 90,
    );

    if (image != null) {
      setState(() {
        _selectedImagePath = image.path;
        _analysis = null;
        _errorMessage = null;
      });
    }
  }

  void _changeImage() {
    setState(() {
      _selectedImagePath = null;
      _analysis = null;
      _errorMessage = null;
    });
  }

  Future<void> _analyzeImage() async {
    if (_selectedImagePath == null) return;

    setState(() {
      _isAnalyzing = true;
      _errorMessage = null;
    });

    try {
      final geminiService = ref.read(geminiServiceProvider);
      final analysis = await geminiService.analyzeImage(_selectedImagePath!);

      setState(() {
        _analysis = analysis;
      });
    } catch (e) {
      setState(() {
        _errorMessage = 'Erreur lors de l\'analyse: $e';
      });
    } finally {
      setState(() {
        _isAnalyzing = false;
      });
    }
  }

  Future<void> _restoreImage() async {
    if (_selectedImagePath == null) return;

    // Vérifier les restaurations gratuites
    final storageService = ref.read(storageServiceProvider);
    if (!storageService.hasFreeRestorationsAvailable) {
      // Rediriger vers l'achat
      if (mounted) {
        final result = await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Restaurations épuisées'),
            content: const Text(
              'Vous avez utilisé toutes vos restaurations gratuites. '
              'Passez Premium pour des restaurations illimitées.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('Annuler'),
              ),
              ElevatedButton(
                onPressed: () {
                  Navigator.pop(context, true);
                  context.push(AppRoutes.purchase);
                },
                child: const Text('Voir Premium'),
              ),
            ],
          ),
        );
        return;
      }
    }

    setState(() {
      _isRestoring = true;
      _errorMessage = null;
    });

    try {
      final geminiService = ref.read(geminiServiceProvider);
      final restoredPath = await geminiService.restoreImage(_selectedImagePath!);

      // Sauvegarder la photo
      final photo = PhotoModel(
        id: const Uuid().v4(),
        originalPath: _selectedImagePath!,
        restoredPath: restoredPath,
        createdAt: DateTime.now(),
        restoredAt: DateTime.now(),
        status: PhotoStatus.restored,
      );

      await storageService.savePhoto(photo);
      await storageService.incrementFreeRestorations();

      if (mounted) {
        context.push(
          AppRoutes.restorationResult,
          extra: {
            'originalPath': _selectedImagePath,
            'restoredPath': restoredPath,
            'photoId': photo.id,
          },
        );
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Erreur lors de la restauration: $e';
      });
    } finally {
      setState(() {
        _isRestoring = false;
      });
    }
  }
}

class _SelectionButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _SelectionButton({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.surfaceLight,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          width: 120,
          padding: const EdgeInsets.symmetric(vertical: 24),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppColors.divider),
          ),
          child: Column(
            children: [
              Icon(icon, size: 32, color: AppColors.primary),
              const SizedBox(height: 12),
              Text(
                label,
                style: const TextStyle(
                  fontWeight: FontWeight.w500,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DefectChip extends StatelessWidget {
  final String label;
  final IconData icon;

  const _DefectChip({
    required this.label,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.error.withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: AppColors.error),
          const SizedBox(width: 6),
          Text(
            label,
            style: const TextStyle(
              fontSize: 12,
              color: AppColors.error,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}
