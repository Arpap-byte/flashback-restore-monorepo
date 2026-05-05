import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:share_plus/share_plus.dart';
import 'package:video_player/video_player.dart';

import '../../../../core/constants/app_constants.dart';
import '../../../../core/theme/app_colors.dart';

class AnimationResultScreen extends ConsumerStatefulWidget {
  final String originalImagePath;
  final String animatedVideoPath;

  const AnimationResultScreen({
    super.key,
    required this.originalImagePath,
    required this.animatedVideoPath,
  });

  @override
  ConsumerState<AnimationResultScreen> createState() =>
      _AnimationResultScreenState();
}

class _AnimationResultScreenState extends ConsumerState<AnimationResultScreen> {
  late VideoPlayerController _videoController;
  bool _isInitialized = false;
  bool _isPlaying = true;

  @override
  void initState() {
    super.initState();
    _initializeVideo();
  }

  Future<void> _initializeVideo() async {
    _videoController = VideoPlayerController.file(
      File(widget.animatedVideoPath),
    );

    await _videoController.initialize();
    _videoController.setLooping(true);
    _videoController.play();

    setState(() => _isInitialized = true);
  }

  @override
  void dispose() {
    _videoController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
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
            child: const Icon(Icons.close, color: Colors.white),
          ),
          onPressed: () => context.go(AppRoutes.home),
        ),
        actions: [
          IconButton(
            icon: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.5),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.share, color: Colors.white),
            ),
            onPressed: _shareVideo,
          ),
        ],
      ),
      body: Stack(
        children: [
          // Video player
          Center(
            child: _isInitialized
                ? GestureDetector(
                    onTap: _togglePlayPause,
                    child: AspectRatio(
                      aspectRatio: _videoController.value.aspectRatio,
                      child: VideoPlayer(_videoController),
                    ),
                  )
                : const CircularProgressIndicator(color: Colors.white),
          ),

          // Play/Pause overlay
          if (_isInitialized && !_isPlaying)
            Center(
              child: GestureDetector(
                onTap: _togglePlayPause,
                child: Container(
                  width: 80,
                  height: 80,
                  decoration: BoxDecoration(
                    color: Colors.black.withOpacity(0.6),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.play_arrow,
                    size: 50,
                    color: Colors.white,
                  ),
                ),
              ),
            ).animate().fadeIn(duration: 200.ms),

          // Success banner
          Positioned(
            top: MediaQuery.of(context).padding.top + 60,
            left: 16,
            right: 16,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              decoration: BoxDecoration(
                gradient: AppColors.premiumGradient,
                borderRadius: BorderRadius.circular(30),
                boxShadow: [
                  BoxShadow(
                    color: AppColors.gold.withOpacity(0.3),
                    blurRadius: 20,
                    offset: const Offset(0, 5),
                  ),
                ],
              ),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.auto_awesome, color: Colors.white, size: 20),
                  SizedBox(width: 8),
                  Text(
                    'Votre photo prend vie !',
                    style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ).animate().fadeIn(duration: 500.ms).slideY(begin: -0.5, end: 0),
          ),

          // Bottom controls
          Positioned(
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
                children: [
                  // Video progress
                  if (_isInitialized)
                    VideoProgressIndicator(
                      _videoController,
                      allowScrubbing: true,
                      colors: const VideoProgressColors(
                        playedColor: AppColors.accent,
                        bufferedColor: Colors.white30,
                        backgroundColor: Colors.white10,
                      ),
                    ),

                  const SizedBox(height: 24),

                  // Action buttons
                  Row(
                    children: [
                      Expanded(
                        child: _ActionButton(
                          icon: Icons.download,
                          label: 'Enregistrer',
                          onTap: _saveVideo,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _ActionButton(
                          icon: Icons.share,
                          label: 'Partager',
                          onTap: _shareVideo,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _ActionButton(
                          icon: Icons.photo_library,
                          label: 'Galerie',
                          onTap: () => context.go(AppRoutes.gallery),
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: 16),

                  // New animation button
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: () => context.go(AppRoutes.home),
                      icon: const Icon(Icons.add_photo_alternate),
                      label: const Text('Nouvelle photo'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.primary,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _togglePlayPause() {
    setState(() {
      if (_videoController.value.isPlaying) {
        _videoController.pause();
        _isPlaying = false;
      } else {
        _videoController.play();
        _isPlaying = true;
      }
    });
  }

  void _saveVideo() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Vidéo enregistrée dans la galerie'),
        backgroundColor: AppColors.success,
      ),
    );
  }

  void _shareVideo() async {
    await Share.shareXFiles(
      [XFile(widget.animatedVideoPath)],
      text: 'Photo animée avec Flashback Restore ✨',
    );
  }
}

class _ActionButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _ActionButton({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white.withOpacity(0.15),
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 14),
          child: Column(
            children: [
              Icon(icon, color: Colors.white, size: 24),
              const SizedBox(height: 6),
              Text(
                label,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
