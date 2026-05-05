import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:photo_view/photo_view.dart';
import 'package:share_plus/share_plus.dart';
import 'package:video_player/video_player.dart';

import '../../../../core/constants/app_constants.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../shared/models/photo_model.dart';
import '../../../../shared/services/storage_service.dart';

/// Provider pour une photo spécifique
final photoDetailProvider =
    FutureProvider.family<PhotoModel?, String>((ref, id) async {
  final storageService = ref.read(storageServiceProvider);
  await storageService.initialize();
  return storageService.getPhoto(id);
});

class PhotoDetailScreen extends ConsumerStatefulWidget {
  final String photoId;

  const PhotoDetailScreen({
    super.key,
    required this.photoId,
  });

  @override
  ConsumerState<PhotoDetailScreen> createState() => _PhotoDetailScreenState();
}

class _PhotoDetailScreenState extends ConsumerState<PhotoDetailScreen> {
  bool _showOriginal = false;
  bool _showVideo = false;
  VideoPlayerController? _videoController;

  @override
  void dispose() {
    _videoController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final photoAsync = ref.watch(photoDetailProvider(widget.photoId));

    return Scaffold(
      backgroundColor: Colors.black,
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.black.withOpacity(0.5),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.arrow_back, color: Colors.white),
          ),
          onPressed: () => context.pop(),
        ),
        actions: [
          photoAsync.maybeWhen(
            data: (photo) => photo != null
                ? PopupMenuButton<String>(
                    icon: Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.black.withOpacity(0.5),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.more_vert, color: Colors.white),
                    ),
                    onSelected: (value) => _handleMenuAction(value, photo),
                    itemBuilder: (context) => [
                      const PopupMenuItem(
                        value: 'share',
                        child: Row(
                          children: [
                            Icon(Icons.share),
                            SizedBox(width: 12),
                            Text('Partager'),
                          ],
                        ),
                      ),
                      const PopupMenuItem(
                        value: 'save',
                        child: Row(
                          children: [
                            Icon(Icons.download),
                            SizedBox(width: 12),
                            Text('Enregistrer'),
                          ],
                        ),
                      ),
                      if (!photo.isAnimated && photo.restoredPath != null)
                        const PopupMenuItem(
                          value: 'animate',
                          child: Row(
                            children: [
                              Icon(Icons.movie_filter),
                              SizedBox(width: 12),
                              Text('Animer'),
                            ],
                          ),
                        ),
                      const PopupMenuItem(
                        value: 'delete',
                        child: Row(
                          children: [
                            Icon(Icons.delete, color: AppColors.error),
                            SizedBox(width: 12),
                            Text('Supprimer',
                                style: TextStyle(color: AppColors.error)),
                          ],
                        ),
                      ),
                    ],
                  )
                : const SizedBox(),
            orElse: () => const SizedBox(),
          ),
        ],
      ),
      body: photoAsync.when(
        data: (photo) {
          if (photo == null) {
            return const Center(
              child: Text(
                'Photo non trouvée',
                style: TextStyle(color: Colors.white),
              ),
            );
          }

          return Stack(
            children: [
              // Main content
              _showVideo && photo.animatedVideoPath != null
                  ? _buildVideoPlayer(photo.animatedVideoPath!)
                  : _buildImageViewer(photo),

              // Bottom controls
              _buildBottomControls(photo),
            ],
          );
        },
        loading: () => const Center(
          child: CircularProgressIndicator(color: Colors.white),
        ),
        error: (error, stack) => Center(
          child: Text(
            'Erreur: $error',
            style: const TextStyle(color: Colors.white),
          ),
        ),
      ),
    );
  }

  Widget _buildImageViewer(PhotoModel photo) {
    final imagePath = _showOriginal
        ? photo.originalPath
        : (photo.restoredPath ?? photo.originalPath);

    return PhotoView(
      imageProvider: FileImage(File(imagePath)),
      minScale: PhotoViewComputedScale.contained,
      maxScale: PhotoViewComputedScale.covered * 3,
      backgroundDecoration: const BoxDecoration(color: Colors.black),
    );
  }

  Widget _buildVideoPlayer(String videoPath) {
    if (_videoController == null) {
      _videoController = VideoPlayerController.file(File(videoPath))
        ..initialize().then((_) {
          setState(() {});
          _videoController!.setLooping(true);
          _videoController!.play();
        });
    }

    if (!_videoController!.value.isInitialized) {
      return const Center(
        child: CircularProgressIndicator(color: Colors.white),
      );
    }

    return Center(
      child: AspectRatio(
        aspectRatio: _videoController!.value.aspectRatio,
        child: VideoPlayer(_videoController!),
      ),
    );
  }

  Widget _buildBottomControls(PhotoModel photo) {
    return Positioned(
      bottom: 0,
      left: 0,
      right: 0,
      child: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.bottomCenter,
            end: Alignment.topCenter,
            colors: [
              Colors.black.withOpacity(0.8),
              Colors.transparent,
            ],
          ),
        ),
        padding: EdgeInsets.fromLTRB(
          16,
          48,
          16,
          MediaQuery.of(context).padding.bottom + 16,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Photo info
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _formatDate(photo.createdAt),
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          if (photo.restoredPath != null) ...[
                            const Icon(Icons.check_circle,
                                size: 14, color: AppColors.success),
                            const SizedBox(width: 4),
                            const Text(
                              'Restaurée',
                              style: TextStyle(
                                color: AppColors.success,
                                fontSize: 12,
                              ),
                            ),
                            const SizedBox(width: 12),
                          ],
                          if (photo.isAnimated) ...[
                            const Icon(Icons.movie_filter,
                                size: 14, color: AppColors.accent),
                            const SizedBox(width: 4),
                            const Text(
                              'Animée',
                              style: TextStyle(
                                color: AppColors.accent,
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),

            const SizedBox(height: 16),

            // Toggle buttons
            if (photo.restoredPath != null || photo.isAnimated)
              Row(
                children: [
                  if (photo.restoredPath != null) ...[
                    Expanded(
                      child: _ToggleButton(
                        label: 'Original',
                        isSelected: _showOriginal && !_showVideo,
                        onTap: () => setState(() {
                          _showOriginal = true;
                          _showVideo = false;
                        }),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: _ToggleButton(
                        label: 'Restaurée',
                        isSelected: !_showOriginal && !_showVideo,
                        onTap: () => setState(() {
                          _showOriginal = false;
                          _showVideo = false;
                        }),
                      ),
                    ),
                  ],
                  if (photo.isAnimated) ...[
                    const SizedBox(width: 8),
                    Expanded(
                      child: _ToggleButton(
                        label: 'Vidéo',
                        icon: Icons.play_arrow,
                        isSelected: _showVideo,
                        onTap: () => setState(() {
                          _showVideo = true;
                        }),
                      ),
                    ),
                  ],
                ],
              ),
          ],
        ),
      ),
    );
  }

  void _handleMenuAction(String action, PhotoModel photo) async {
    switch (action) {
      case 'share':
        final path = photo.restoredPath ?? photo.originalPath;
        await Share.shareXFiles([XFile(path)]);
        break;

      case 'save':
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Photo enregistrée'),
            backgroundColor: AppColors.success,
          ),
        );
        break;

      case 'animate':
        context.push(
          AppRoutes.animation,
          extra: {'imagePath': photo.restoredPath ?? photo.originalPath},
        );
        break;

      case 'delete':
        final confirm = await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Supprimer la photo ?'),
            content: const Text(
              'Cette action est irréversible. La photo et tous ses fichiers associés seront supprimés.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('Annuler'),
              ),
              ElevatedButton(
                onPressed: () => Navigator.pop(context, true),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.error,
                ),
                child: const Text('Supprimer'),
              ),
            ],
          ),
        );

        if (confirm == true) {
          final storageService = ref.read(storageServiceProvider);
          await storageService.deletePhoto(photo.id);

          if (mounted) {
            context.pop();
          }
        }
        break;
    }
  }

  String _formatDate(DateTime date) {
    final months = [
      'janvier',
      'février',
      'mars',
      'avril',
      'mai',
      'juin',
      'juillet',
      'août',
      'septembre',
      'octobre',
      'novembre',
      'décembre'
    ];
    return '${date.day} ${months[date.month - 1]} ${date.year}';
  }
}

class _ToggleButton extends StatelessWidget {
  final String label;
  final IconData? icon;
  final bool isSelected;
  final VoidCallback onTap;

  const _ToggleButton({
    required this.label,
    this.icon,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: isSelected ? AppColors.primary : Colors.white.withOpacity(0.15),
      borderRadius: BorderRadius.circular(10),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (icon != null) ...[
                Icon(icon, size: 16, color: Colors.white),
                const SizedBox(width: 6),
              ],
              Text(
                label,
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w600,
                  fontSize: 13,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
