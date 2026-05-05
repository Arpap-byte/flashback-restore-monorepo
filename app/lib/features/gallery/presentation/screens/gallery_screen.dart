import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../shared/models/photo_model.dart';
import '../../../../shared/services/storage_service.dart';

/// Provider pour la liste des photos
final photosProvider = FutureProvider<List<PhotoModel>>((ref) async {
  final storageService = ref.read(storageServiceProvider);
  await storageService.initialize();
  return storageService.getAllPhotos();
});

class GalleryScreen extends ConsumerStatefulWidget {
  const GalleryScreen({super.key});

  @override
  ConsumerState<GalleryScreen> createState() => _GalleryScreenState();
}

class _GalleryScreenState extends ConsumerState<GalleryScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  GalleryFilter _filter = GalleryFilter.all;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final photosAsync = ref.watch(photosProvider);

    return Scaffold(
      backgroundColor: AppColors.backgroundLight,
      appBar: AppBar(
        title: const Text('Ma galerie'),
        bottom: TabBar(
          controller: _tabController,
          onTap: (index) {
            setState(() {
              _filter = GalleryFilter.values[index];
            });
          },
          labelColor: AppColors.primary,
          unselectedLabelColor: AppColors.textSecondary,
          indicatorColor: AppColors.primary,
          tabs: const [
            Tab(text: 'Tout'),
            Tab(text: 'Restaurées'),
            Tab(text: 'Animées'),
          ],
        ),
      ),
      body: photosAsync.when(
        data: (photos) {
          final filteredPhotos = _filterPhotos(photos);

          if (filteredPhotos.isEmpty) {
            return _buildEmptyState();
          }

          return GridView.builder(
            padding: const EdgeInsets.all(16),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
              childAspectRatio: 0.8,
            ),
            itemCount: filteredPhotos.length,
            itemBuilder: (context, index) {
              final photo = filteredPhotos[index];
              return _PhotoCard(
                photo: photo,
                index: index,
                onTap: () => context.push('/gallery/${photo.id}'),
              );
            },
          );
        },
        loading: () => const Center(
          child: CircularProgressIndicator(),
        ),
        error: (error, stack) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, size: 48, color: AppColors.error),
              const SizedBox(height: 16),
              Text('Erreur: $error'),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () => ref.refresh(photosProvider),
                child: const Text('Réessayer'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  List<PhotoModel> _filterPhotos(List<PhotoModel> photos) {
    switch (_filter) {
      case GalleryFilter.all:
        return photos;
      case GalleryFilter.restored:
        return photos.where((p) => p.restoredPath != null).toList();
      case GalleryFilter.animated:
        return photos.where((p) => p.isAnimated).toList();
    }
  }

  Widget _buildEmptyState() {
    String message;
    IconData icon;

    switch (_filter) {
      case GalleryFilter.all:
        message = 'Aucune photo pour le moment';
        icon = Icons.photo_library_outlined;
        break;
      case GalleryFilter.restored:
        message = 'Aucune photo restaurée';
        icon = Icons.auto_fix_high;
        break;
      case GalleryFilter.animated:
        message = 'Aucune photo animée';
        icon = Icons.movie_filter_outlined;
        break;
    }

    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 100,
            height: 100,
            decoration: BoxDecoration(
              color: AppColors.primary.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(icon, size: 50, color: AppColors.primary),
          ).animate().scale(duration: 500.ms, curve: Curves.elasticOut),
          const SizedBox(height: 24),
          Text(
            message,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            'Commencez par restaurer une photo',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: AppColors.textSecondary,
                ),
          ),
        ],
      ),
    );
  }
}

enum GalleryFilter {
  all,
  restored,
  animated,
}

class _PhotoCard extends StatelessWidget {
  final PhotoModel photo;
  final int index;
  final VoidCallback onTap;

  const _PhotoCard({
    required this.photo,
    required this.index,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final displayPath = photo.restoredPath ?? photo.originalPath;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.1),
                blurRadius: 10,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: Stack(
              fit: StackFit.expand,
              children: [
                // Image
                Image.file(
                  File(displayPath),
                  fit: BoxFit.cover,
                ),

                // Gradient overlay
                Positioned(
                  bottom: 0,
                  left: 0,
                  right: 0,
                  child: Container(
                    height: 80,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.bottomCenter,
                        end: Alignment.topCenter,
                        colors: [
                          Colors.black.withOpacity(0.7),
                          Colors.transparent,
                        ],
                      ),
                    ),
                  ),
                ),

                // Status badges
                Positioned(
                  top: 8,
                  right: 8,
                  child: Row(
                    children: [
                      if (photo.restoredPath != null)
                        _StatusBadge(
                          icon: Icons.auto_fix_high,
                          color: AppColors.success,
                        ),
                      if (photo.isAnimated) ...[
                        const SizedBox(width: 4),
                        _StatusBadge(
                          icon: Icons.movie_filter,
                          color: AppColors.accent,
                        ),
                      ],
                    ],
                  ),
                ),

                // Date
                Positioned(
                  bottom: 8,
                  left: 8,
                  right: 8,
                  child: Text(
                    _formatDate(photo.createdAt),
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    )
        .animate()
        .fadeIn(delay: Duration(milliseconds: 50 * index), duration: 400.ms)
        .slideY(begin: 0.1, end: 0);
  }

  String _formatDate(DateTime date) {
    final now = DateTime.now();
    final diff = now.difference(date);

    if (diff.inDays == 0) {
      return 'Aujourd\'hui';
    } else if (diff.inDays == 1) {
      return 'Hier';
    } else if (diff.inDays < 7) {
      return 'Il y a ${diff.inDays} jours';
    } else {
      return '${date.day}/${date.month}/${date.year}';
    }
  }
}

class _StatusBadge extends StatelessWidget {
  final IconData icon;
  final Color color;

  const _StatusBadge({
    required this.icon,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Icon(icon, size: 14, color: Colors.white),
    );
  }
}
