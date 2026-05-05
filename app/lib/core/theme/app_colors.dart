import 'package:flutter/material.dart';

/// Palette de couleurs de l'application
/// Design épuré avec des tons chauds évoquant la nostalgie des photos anciennes
class AppColors {
  AppColors._();

  // ============ PRIMARY COLORS ============
  /// Couleur principale - Ambre doré (évoque les photos sépia)
  static const Color primary = Color(0xFFD4A574);
  static const Color primaryLight = Color(0xFFE8C9A8);
  static const Color primaryDark = Color(0xFFB8895A);

  /// Couleur secondaire - Bleu profond (contraste élégant)
  static const Color secondary = Color(0xFF2C3E50);
  static const Color secondaryLight = Color(0xFF34495E);
  static const Color secondaryDark = Color(0xFF1A252F);

  // ============ ACCENT COLORS ============
  /// Couleur d'accent pour les animations/premium
  static const Color accent = Color(0xFFE74C3C);
  static const Color accentLight = Color(0xFFFF6B5B);
  static const Color gold = Color(0xFFFFD700);

  // ============ SEMANTIC COLORS ============
  static const Color success = Color(0xFF27AE60);
  static const Color warning = Color(0xFFF39C12);
  static const Color error = Color(0xFFE74C3C);
  static const Color info = Color(0xFF3498DB);

  // ============ BACKGROUND COLORS ============
  static const Color backgroundLight = Color(0xFFFAF8F5);
  static const Color backgroundDark = Color(0xFF1A1A1A);

  static const Color surfaceLight = Color(0xFFFFFFFF);
  static const Color surfaceDark = Color(0xFF2D2D2D);

  // ============ TEXT COLORS ============
  static const Color textPrimary = Color(0xFF2C3E50);
  static const Color textSecondary = Color(0xFF7F8C8D);
  static const Color textLight = Color(0xFFF5F5F5);
  static const Color textSecondaryDark = Color(0xFFB0B0B0);

  // ============ DIVIDER COLORS ============
  static const Color divider = Color(0xFFECECEC);
  static const Color dividerDark = Color(0xFF404040);

  // ============ GRADIENT COLORS ============
  static const LinearGradient primaryGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [primary, primaryDark],
  );

  static const LinearGradient premiumGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFFFFD700), Color(0xFFFFA500)],
  );

  static const LinearGradient darkGradient = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [Colors.transparent, Colors.black87],
  );

  // ============ SHIMMER COLORS ============
  static const Color shimmerBase = Color(0xFFE0E0E0);
  static const Color shimmerHighlight = Color(0xFFF5F5F5);
  static const Color shimmerBaseDark = Color(0xFF3D3D3D);
  static const Color shimmerHighlightDark = Color(0xFF4D4D4D);
}
