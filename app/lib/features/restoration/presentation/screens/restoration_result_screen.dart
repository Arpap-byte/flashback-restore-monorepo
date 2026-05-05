import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:share_plus/share_plus.dart';

import '../../../../core/constants/app_constants.dart';
import '../../../../core/theme/app_colors.dart';

class RestorationResultScreen extends ConsumerStatefulWidget {
  final String originalImagePath;
  final String restoredImagePath;

  const RestorationResultScreen({
    super.key,
    required this.originalImagePath,
    required this.restoredImagePath,
  });

  @override
  ConsumerState<RestorationResultScreen> createState() =>
      _RestorationResultScreenState();
}

class _RestorationResultScreenState
    extends ConsumerState<RestorationResultScreen> {
  bool _showOriginal = false;
  double _sliderValue = 1.0; // 0 = original, 1 = restored

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.backgroundLight,
      appBar: AppBar(
        title: const Text('Restauration terminée'),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => context.go(AppRoutes.home),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.share),
            onPressed: _shareImage,
          ),
        ],
      ),
      body: Column(
        children: [
          // Success banner
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            color: AppColors.success.withOpacity(0.1),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.check_circle, color: AppColors.success),
                const SizedBox(width: 12),
                Text(
                  'Photo restaurée avec succès !',
                  style: TextStyle(
                    color: AppColors.success,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ).animate().fadeIn(duration: 400.ms),

          // Image comparison
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  // Image container
                  Expanded(
                    child: Container(
                      width: double.infinity,
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
                            // Original image (bottom)
                            Image.file(
                              File(widget.originalImagePath),
                              fit: BoxFit.cover,
                            ),
                            // Restored image (top with clip)
                            ClipRect(
                              clipper: _ImageClipper(_sliderValue),
                              child: Image.file(
                                File(widget.restoredImagePath),
                                fit: BoxFit.cover,
                              ),
                            ),
                            // Slider line
                            Positioned(
                              left: MediaQuery.of(context).size.width *
                                      _sliderValue -
                                  32, // Adjust for padding
                              top: 0,
                              bottom: 0,
                              child: Container(
                                width: 3,
                                color: Colors.white,
                                child: Center(
                                  child: Container(
                                    width: 40,
                                    height: 40,
                                    decoration: BoxDecoration(
                                      color: Colors.white,
                                      shape: BoxShape.circle,
                                      boxShadow: [
                                        BoxShadow(
                                          color: Colors.black.withOpacity(0.2),
                                          blurRadius: 8,
                                        ),
                                      ],
                                    ),
                                    child: const Icon(
                                      Icons.compare_arrows,
                                      color: AppColors.primary,
                                    ),
                                  ),
                                ),
                              ),
                            ),
                            // Labels
                            Positioned(
                              top: 16,
                              left: 16,
                              child: _ImageLabel(
                                label: 'Avant',
                                isVisible: _sliderValue > 0.15,
                              ),
                            ),
                            Positioned(
                              top: 16,
                              right: 16,
                              child: _ImageLabel(
                                label: 'Après',
                                isVisible: _sliderValue < 0.85,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  )
                      .animate()
                      .fadeIn(delay: 200.ms, duration: 500.ms)
                      .scale(begin: const Offset(0.95, 0.95)),

                  const SizedBox(height: 16),

                  // Comparison slider
                  Row(
                    children: [
                      const Text(
                        'Avant',
                        style: TextStyle(
                          color: AppColors.textSecondary,
                          fontSize: 12,
                        ),
                      ),
                      Expanded(
                        child: Slider(
                          value: _sliderValue,
                          onChanged: (value) {
                            setState(() => _sliderValue = value);
                          },
                          activeColor: AppColors.primary,
                          inactiveColor: AppColors.divider,
                        ),
                      ),
                      const Text(
                        'Après',
                        style: TextStyle(
                          color: AppColors.textSecondary,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: 16),

                  // Toggle buttons
                  Row(
                    children: [
                      Expanded(
                        child: _ToggleButton(
                          label: 'Original',
                          isSelected: _sliderValue == 0,
                          onTap: () => setState(() => _sliderValue = 0),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _ToggleButton(
                          label: 'Restaurée',
                          isSelected: _sliderValue == 1,
                          onTap: () => setState(() => _sliderValue = 1),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),

          // Action buttons
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.surfaceLight,
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.05),
                  blurRadius: 10,
                  offset: const Offset(0, -5),
                ),
              ],
            ),
            child: SafeArea(
              child: Column(
                children: [
                  // Animate button
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _animatePhoto,
                      icon: const Icon(Icons.movie_filter_outlined),
                      label: const Text('Animer cette photo'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.accent,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  // Secondary actions
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: _saveToGallery,
                          icon: const Icon(Icons.download),
                          label: const Text('Enregistrer'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () => context.go(AppRoutes.home),
                          icon: const Icon(Icons.home),
                          label: const Text('Accueil'),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _shareImage() async {
    await Share.shareXFiles(
      [XFile(widget.restoredImagePath)],
      text: 'Photo restaurée avec Flashback Restore',
    );
  }

  void _saveToGallery() async {
    // Afficher un snackbar de confirmation
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Photo enregistrée dans la galerie'),
        backgroundColor: AppColors.success,
      ),
    );
  }

  void _animatePhoto() {
    context.push(
      AppRoutes.animation,
      extra: {'imagePath': widget.restoredImagePath},
    );
  }
}

class _ImageClipper extends CustomClipper<Rect> {
  final double percentage;

  _ImageClipper(this.percentage);

  @override
  Rect getClip(Size size) {
    return Rect.fromLTRB(0, 0, size.width * percentage, size.height);
  }

  @override
  bool shouldReclip(_ImageClipper oldClipper) {
    return percentage != oldClipper.percentage;
  }
}

class _ImageLabel extends StatelessWidget {
  final String label;
  final bool isVisible;

  const _ImageLabel({
    required this.label,
    required this.isVisible,
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedOpacity(
      opacity: isVisible ? 1.0 : 0.0,
      duration: const Duration(milliseconds: 200),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: Colors.black.withOpacity(0.6),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(
          label,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 12,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }
}

class _ToggleButton extends StatelessWidget {
  final String label;
  final bool isSelected;
  final VoidCallback onTap;

  const _ToggleButton({
    required this.label,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: isSelected ? AppColors.primary : AppColors.surfaceLight,
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: isSelected ? AppColors.primary : AppColors.divider,
            ),
          ),
          child: Center(
            child: Text(
              label,
              style: TextStyle(
                color: isSelected ? Colors.white : AppColors.textPrimary,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
