import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/constants/app_constants.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../shared/services/animation_service.dart';
import '../../../../shared/services/purchase_service.dart';

class AnimationScreen extends ConsumerStatefulWidget {
  final String imagePath;

  const AnimationScreen({
    super.key,
    required this.imagePath,
  });

  @override
  ConsumerState<AnimationScreen> createState() => _AnimationScreenState();
}

class _AnimationScreenState extends ConsumerState<AnimationScreen>
    with SingleTickerProviderStateMixin {
  AnimationStyle _selectedStyle = AnimationStyle.subtle;
  bool _isAnimating = false;
  double _progress = 0;
  String? _errorMessage;

  late AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isPremium = ref.watch(isPremiumProvider);
    final credits = ref.watch(animationCreditsProvider);

    return Scaffold(
      backgroundColor: AppColors.backgroundLight,
      appBar: AppBar(
        title: const Text('Animer la photo'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: Column(
        children: [
          // Premium/Credits info
          _buildCreditsInfo(isPremium, credits),

          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Image preview
                  _buildImagePreview(),

                  const SizedBox(height: 24),

                  // Style selection
                  Text(
                    'Style d\'animation',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  const SizedBox(height: 12),
                  _buildStyleSelection(),

                  const SizedBox(height: 24),

                  // Info card
                  _buildInfoCard(),

                  if (_errorMessage != null) ...[
                    const SizedBox(height: 16),
                    _buildErrorCard(),
                  ],
                ],
              ),
            ),
          ),

          // Action button
          _buildActionButton(isPremium, credits),
        ],
      ),
    );
  }

  Widget _buildCreditsInfo(
    AsyncValue<bool> isPremium,
    AsyncValue<int> credits,
  ) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      color: AppColors.secondary.withOpacity(0.05),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          isPremium.when(
            data: (premium) => premium
                ? Row(
                    children: [
                      const Icon(Icons.all_inclusive,
                          size: 18, color: AppColors.gold),
                      const SizedBox(width: 8),
                      const Text(
                        'Animations illimitées',
                        style: TextStyle(
                          color: AppColors.gold,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  )
                : credits.when(
                    data: (c) => Row(
                      children: [
                        Icon(
                          c > 0 ? Icons.movie_filter : Icons.movie_filter_outlined,
                          size: 18,
                          color: c > 0 ? AppColors.primary : AppColors.error,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          c > 0
                              ? '$c crédit${c > 1 ? 's' : ''} disponible${c > 1 ? 's' : ''}'
                              : 'Aucun crédit',
                          style: TextStyle(
                            color: c > 0 ? AppColors.textPrimary : AppColors.error,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        if (c == 0) ...[
                          const SizedBox(width: 12),
                          TextButton(
                            onPressed: () => context.push(AppRoutes.purchase),
                            child: const Text('Acheter'),
                          ),
                        ],
                      ],
                    ),
                    loading: () => const SizedBox(),
                    error: (_, __) => const SizedBox(),
                  ),
            loading: () => const SizedBox(),
            error: (_, __) => const SizedBox(),
          ),
        ],
      ),
    );
  }

  Widget _buildImagePreview() {
    return Container(
      width: double.infinity,
      height: 300,
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
              File(widget.imagePath),
              fit: BoxFit.cover,
            ),
            if (_isAnimating)
              Container(
                color: Colors.black.withOpacity(0.6),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // Animated magic wand
                    AnimatedBuilder(
                      animation: _pulseController,
                      builder: (context, child) {
                        return Transform.scale(
                          scale: 1 + (_pulseController.value * 0.1),
                          child: Container(
                            width: 80,
                            height: 80,
                            decoration: BoxDecoration(
                              color: AppColors.accent.withOpacity(0.2),
                              shape: BoxShape.circle,
                            ),
                            child: const Icon(
                              Icons.auto_fix_high,
                              size: 40,
                              color: Colors.white,
                            ),
                          ),
                        );
                      },
                    ),
                    const SizedBox(height: 24),
                    const Text(
                      'Création de l\'animation...',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 16),
                    SizedBox(
                      width: 200,
                      child: LinearProgressIndicator(
                        value: _progress > 0 ? _progress : null,
                        backgroundColor: Colors.white.withOpacity(0.2),
                        valueColor: const AlwaysStoppedAnimation<Color>(
                          AppColors.accent,
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Cela peut prendre jusqu\'à 2 minutes',
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.7),
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ),
      ),
    ).animate().fadeIn(duration: 400.ms).scale(begin: const Offset(0.95, 0.95));
  }

  Widget _buildStyleSelection() {
    return Row(
      children: AnimationStyle.values.map((style) {
        final isSelected = style == _selectedStyle;
        return Expanded(
          child: Padding(
            padding: EdgeInsets.only(
              right: style != AnimationStyle.values.last ? 12 : 0,
            ),
            child: _StyleCard(
              style: style,
              isSelected: isSelected,
              onTap: () => setState(() => _selectedStyle = style),
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildInfoCard() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.info.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.info.withOpacity(0.2)),
      ),
      child: Row(
        children: [
          const Icon(Icons.info_outline, color: AppColors.info),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Animation intelligente',
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    color: AppColors.info,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'L\'IA détecte automatiquement les visages et crée des mouvements naturels.',
                  style: TextStyle(
                    fontSize: 12,
                    color: AppColors.info.withOpacity(0.8),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorCard() {
    return Container(
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
    );
  }

  Widget _buildActionButton(
    AsyncValue<bool> isPremium,
    AsyncValue<int> credits,
  ) {
    final canAnimate = isPremium.maybeWhen(
          data: (p) => p || credits.maybeWhen(data: (c) => c > 0, orElse: () => false),
          orElse: () => false,
        );

    return Container(
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
        child: SizedBox(
          width: double.infinity,
          child: ElevatedButton.icon(
            onPressed: _isAnimating
                ? null
                : (canAnimate ? _startAnimation : () => context.push(AppRoutes.purchase)),
            icon: Icon(_isAnimating
                ? Icons.hourglass_empty
                : (canAnimate ? Icons.movie_filter : Icons.shopping_cart)),
            label: Text(_isAnimating
                ? 'Animation en cours...'
                : (canAnimate ? 'Créer l\'animation' : 'Acheter des crédits')),
            style: ElevatedButton.styleFrom(
              backgroundColor: canAnimate ? AppColors.accent : AppColors.primary,
              padding: const EdgeInsets.symmetric(vertical: 16),
              disabledBackgroundColor: AppColors.accent.withOpacity(0.5),
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _startAnimation() async {
    setState(() {
      _isAnimating = true;
      _errorMessage = null;
      _progress = 0;
    });

    try {
      final animationService = ref.read(animationServiceProvider);

      // Simuler la progression
      for (int i = 1; i <= 10; i++) {
        await Future.delayed(const Duration(seconds: 1));
        if (mounted) {
          setState(() => _progress = i / 10);
        }
      }

      final videoPath = await animationService.animatePhoto(
        widget.imagePath,
        style: _selectedStyle,
      );

      if (mounted) {
        context.push(
          AppRoutes.animationResult,
          extra: {
            'originalPath': widget.imagePath,
            'videoPath': videoPath,
          },
        );
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Erreur lors de l\'animation: $e';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isAnimating = false;
          _progress = 0;
        });
      }
    }
  }
}

class _StyleCard extends StatelessWidget {
  final AnimationStyle style;
  final bool isSelected;
  final VoidCallback onTap;

  const _StyleCard({
    required this.style,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    String label;
    String description;
    IconData icon;

    switch (style) {
      case AnimationStyle.subtle:
        label = 'Subtil';
        description = 'Léger';
        icon = Icons.air;
        break;
      case AnimationStyle.moderate:
        label = 'Modéré';
        description = 'Équilibré';
        icon = Icons.waves;
        break;
      case AnimationStyle.dynamic:
        label = 'Dynamique';
        description = 'Expressif';
        icon = Icons.flash_on;
        break;
    }

    return Material(
      color: isSelected ? AppColors.accent : AppColors.surfaceLight,
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 8),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: isSelected ? AppColors.accent : AppColors.divider,
              width: isSelected ? 2 : 1,
            ),
          ),
          child: Column(
            children: [
              Icon(
                icon,
                color: isSelected ? Colors.white : AppColors.textSecondary,
              ),
              const SizedBox(height: 8),
              Text(
                label,
                style: TextStyle(
                  fontWeight: FontWeight.w600,
                  color: isSelected ? Colors.white : AppColors.textPrimary,
                ),
              ),
              Text(
                description,
                style: TextStyle(
                  fontSize: 10,
                  color: isSelected
                      ? Colors.white.withOpacity(0.8)
                      : AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
