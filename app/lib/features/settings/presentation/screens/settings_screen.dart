import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../../core/constants/app_constants.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../shared/services/storage_service.dart';
import '../../../../shared/services/purchase_service.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  @override
  Widget build(BuildContext context) {
    final isPremium = ref.watch(isPremiumProvider);
    final storageService = ref.watch(storageServiceProvider);

    return Scaffold(
      backgroundColor: AppColors.backgroundLight,
      appBar: AppBar(
        title: const Text('Paramètres'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Premium card
          _buildPremiumCard(isPremium),

          const SizedBox(height: 24),

          // Account section
          _buildSectionTitle('Compte'),
          _SettingsCard(
            children: [
              _SettingsTile(
                icon: Icons.restore,
                title: 'Restaurer les achats',
                subtitle: 'Récupérer vos achats précédents',
                onTap: _restorePurchases,
              ),
              const Divider(height: 1),
              _SettingsTile(
                icon: Icons.history,
                title: 'Restaurations gratuites',
                subtitle:
                    '${storageService.freeRestorationsRemaining}/${AppConstants.freeRestorationsLimit} restantes',
                trailing: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: storageService.hasFreeRestorationsAvailable
                        ? AppColors.success.withOpacity(0.1)
                        : AppColors.error.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    '${storageService.freeRestorationsRemaining}',
                    style: TextStyle(
                      color: storageService.hasFreeRestorationsAvailable
                          ? AppColors.success
                          : AppColors.error,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(height: 24),

          // Storage section
          _buildSectionTitle('Stockage'),
          _SettingsCard(
            children: [
              FutureBuilder<int>(
                future: storageService.getUsedStorageBytes(),
                builder: (context, snapshot) {
                  final size = snapshot.data ?? 0;
                  return _SettingsTile(
                    icon: Icons.storage,
                    title: 'Espace utilisé',
                    subtitle: storageService.formatStorageSize(size),
                  );
                },
              ),
              const Divider(height: 1),
              _SettingsTile(
                icon: Icons.delete_sweep,
                title: 'Vider le cache',
                subtitle: 'Libérer de l\'espace',
                onTap: _clearCache,
                textColor: AppColors.warning,
              ),
            ],
          ),

          const SizedBox(height: 24),

          // Support section
          _buildSectionTitle('Support'),
          _SettingsCard(
            children: [
              _SettingsTile(
                icon: Icons.help_outline,
                title: 'Aide & FAQ',
                onTap: () => _launchUrl('https://flashbackrestore.app/help'),
              ),
              const Divider(height: 1),
              _SettingsTile(
                icon: Icons.email_outlined,
                title: 'Nous contacter',
                subtitle: 'support@flashbackrestore.app',
                onTap: () => _launchUrl('mailto:support@flashbackrestore.app'),
              ),
              const Divider(height: 1),
              _SettingsTile(
                icon: Icons.star_outline,
                title: 'Noter l\'application',
                onTap: _rateApp,
              ),
            ],
          ),

          const SizedBox(height: 24),

          // Legal section
          _buildSectionTitle('Légal'),
          _SettingsCard(
            children: [
              _SettingsTile(
                icon: Icons.description_outlined,
                title: 'Conditions d\'utilisation',
                onTap: () => _launchUrl('https://flashbackrestore.app/terms'),
              ),
              const Divider(height: 1),
              _SettingsTile(
                icon: Icons.privacy_tip_outlined,
                title: 'Politique de confidentialité',
                onTap: () => _launchUrl('https://flashbackrestore.app/privacy'),
              ),
              const Divider(height: 1),
              _SettingsTile(
                icon: Icons.gavel_outlined,
                title: 'Licences open source',
                onTap: () => showLicensePage(context: context),
              ),
            ],
          ),

          const SizedBox(height: 24),

          // App info
          Center(
            child: Column(
              children: [
                Text(
                  AppConstants.appName,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: AppColors.textSecondary,
                      ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Version ${AppConstants.appVersion}',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppColors.textSecondary,
                      ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 32),

          // Danger zone
          _SettingsCard(
            children: [
              _SettingsTile(
                icon: Icons.delete_forever,
                title: 'Supprimer toutes les données',
                subtitle: 'Effacer photos et paramètres',
                textColor: AppColors.error,
                onTap: _deleteAllData,
              ),
            ],
          ),

          const SizedBox(height: 32),
        ],
      ),
    );
  }

  Widget _buildPremiumCard(AsyncValue<bool> isPremium) {
    return isPremium.when(
      data: (premium) => Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          gradient: premium
              ? AppColors.premiumGradient
              : const LinearGradient(
                  colors: [AppColors.secondary, AppColors.secondaryDark],
                ),
          borderRadius: BorderRadius.circular(20),
          boxShadow: [
            BoxShadow(
              color: (premium ? AppColors.gold : AppColors.secondary)
                  .withOpacity(0.3),
              blurRadius: 20,
              offset: const Offset(0, 10),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  premium ? Icons.workspace_premium : Icons.star_outline,
                  color: Colors.white,
                  size: 32,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        premium ? 'Flashback Premium' : 'Passez Premium',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        premium
                            ? 'Merci pour votre soutien !'
                            : 'Restaurations & animations illimitées',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.8),
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if (!premium) ...[
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () => context.push(AppRoutes.purchase),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.white,
                    foregroundColor: AppColors.secondary,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                  child: const Text('Découvrir les offres'),
                ),
              ),
            ],
          ],
        ),
      ),
      loading: () => const SizedBox(height: 120),
      error: (_, __) => const SizedBox(),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Padding(
      padding: const EdgeInsets.only(left: 4, bottom: 12),
      child: Text(
        title,
        style: Theme.of(context).textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
              color: AppColors.textPrimary,
            ),
      ),
    );
  }

  Future<void> _restorePurchases() async {
    final purchaseService = ref.read(purchaseServiceProvider);
    final result = await purchaseService.restorePurchases();

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(result.message),
          backgroundColor: result.success ? AppColors.success : AppColors.error,
        ),
      );
    }
  }

  Future<void> _clearCache() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Vider le cache ?'),
        content: const Text(
          'Les fichiers temporaires seront supprimés. Vos photos restaurées seront conservées.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Annuler'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Vider'),
          ),
        ],
      ),
    );

    if (confirm == true && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Cache vidé'),
          backgroundColor: AppColors.success,
        ),
      );
    }
  }

  Future<void> _deleteAllData() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Supprimer toutes les données ?'),
        content: const Text(
          'Cette action est irréversible. Toutes vos photos et paramètres seront définitivement supprimés.',
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
      await storageService.clearAllData();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Données supprimées'),
            backgroundColor: AppColors.success,
          ),
        );
      }
    }
  }

  Future<void> _launchUrl(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  void _rateApp() {
    // Platform-specific store URL
    _launchUrl('https://play.google.com/store/apps/details?id=${AppConstants.appBundleId}');
  }
}

class _SettingsCard extends StatelessWidget {
  final List<Widget> children;

  const _SettingsCard({required this.children});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surfaceLight,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.divider),
      ),
      child: Column(children: children),
    );
  }
}

class _SettingsTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? subtitle;
  final Widget? trailing;
  final VoidCallback? onTap;
  final Color? textColor;

  const _SettingsTile({
    required this.icon,
    required this.title,
    this.subtitle,
    this.trailing,
    this.onTap,
    this.textColor,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(
        icon,
        color: textColor ?? AppColors.textSecondary,
      ),
      title: Text(
        title,
        style: TextStyle(
          fontWeight: FontWeight.w500,
          color: textColor ?? AppColors.textPrimary,
        ),
      ),
      subtitle: subtitle != null
          ? Text(
              subtitle!,
              style: TextStyle(
                fontSize: 12,
                color: textColor?.withOpacity(0.7) ?? AppColors.textSecondary,
              ),
            )
          : null,
      trailing: trailing ??
          (onTap != null
              ? Icon(
                  Icons.chevron_right,
                  color: AppColors.textSecondary,
                )
              : null),
      onTap: onTap,
    );
  }
}
