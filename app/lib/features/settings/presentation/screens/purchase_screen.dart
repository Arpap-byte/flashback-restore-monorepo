import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../shared/models/purchase_model.dart';
import '../../../../shared/services/purchase_service.dart';

class PurchaseScreen extends ConsumerStatefulWidget {
  const PurchaseScreen({super.key});

  @override
  ConsumerState<PurchaseScreen> createState() => _PurchaseScreenState();
}

class _PurchaseScreenState extends ConsumerState<PurchaseScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isLoading = false;
  String? _selectedProductId;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.backgroundLight,
      appBar: AppBar(
        title: const Text('Premium & Crédits'),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => context.pop(),
        ),
      ),
      body: Column(
        children: [
          // Header
          _buildHeader(),

          // Tabs
          Container(
            margin: const EdgeInsets.symmetric(horizontal: 16),
            decoration: BoxDecoration(
              color: AppColors.divider,
              borderRadius: BorderRadius.circular(12),
            ),
            child: TabBar(
              controller: _tabController,
              indicator: BoxDecoration(
                color: AppColors.primary,
                borderRadius: BorderRadius.circular(12),
              ),
              labelColor: Colors.white,
              unselectedLabelColor: AppColors.textSecondary,
              tabs: const [
                Tab(text: 'Abonnements'),
                Tab(text: 'Crédits'),
              ],
            ),
          ),

          // Content
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                _buildSubscriptionsList(),
                _buildCreditsList(),
              ],
            ),
          ),

          // Purchase button
          _buildPurchaseButton(),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          Container(
            width: 80,
            height: 80,
            decoration: BoxDecoration(
              gradient: AppColors.premiumGradient,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: AppColors.gold.withOpacity(0.3),
                  blurRadius: 20,
                  offset: const Offset(0, 10),
                ),
              ],
            ),
            child: const Icon(
              Icons.workspace_premium,
              size: 40,
              color: Colors.white,
            ),
          )
              .animate()
              .scale(duration: 500.ms, curve: Curves.elasticOut)
              .fadeIn(),
          const SizedBox(height: 20),
          Text(
            'Flashback Premium',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            'Débloquez toutes les fonctionnalités',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
          ),
          const SizedBox(height: 16),
          // Features
          Wrap(
            spacing: 16,
            runSpacing: 8,
            alignment: WrapAlignment.center,
            children: const [
              _FeatureBadge(icon: Icons.all_inclusive, label: 'Illimité'),
              _FeatureBadge(icon: Icons.auto_fix_high, label: 'Restauration'),
              _FeatureBadge(icon: Icons.movie_filter, label: 'Animation'),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSubscriptionsList() {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: AvailableProducts.subscriptions.length,
      itemBuilder: (context, index) {
        final product = AvailableProducts.subscriptions[index];
        final isSelected = _selectedProductId == product.id;
        final isYearly = product.periodUnit == 'year';

        return _ProductCard(
          product: product,
          isSelected: isSelected,
          badge: isYearly ? 'Économisez 33%' : null,
          badgeColor: AppColors.success,
          onTap: () => setState(() => _selectedProductId = product.id),
        );
      },
    );
  }

  Widget _buildCreditsList() {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: AvailableProducts.animationPacks.length,
      itemBuilder: (context, index) {
        final product = AvailableProducts.animationPacks[index];
        final isSelected = _selectedProductId == product.id;

        String? badge;
        if (product.credits == 5) {
          badge = 'Économisez 20%';
        } else if (product.credits == 10) {
          badge = 'Économisez 35%';
        }

        return _ProductCard(
          product: product,
          isSelected: isSelected,
          badge: badge,
          badgeColor: AppColors.accent,
          onTap: () => setState(() => _selectedProductId = product.id),
        );
      },
    );
  }

  Widget _buildPurchaseButton() {
    return Container(
      padding: EdgeInsets.fromLTRB(
        16,
        16,
        16,
        MediaQuery.of(context).padding.bottom + 16,
      ),
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
      child: Column(
        children: [
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _selectedProductId != null && !_isLoading
                  ? _purchase
                  : null,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.primary,
                disabledBackgroundColor: AppColors.divider,
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
              child: _isLoading
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : Text(
                      _selectedProductId != null
                          ? 'Acheter maintenant'
                          : 'Sélectionnez une offre',
                    ),
            ),
          ),
          const SizedBox(height: 12),
          TextButton(
            onPressed: _restorePurchases,
            child: const Text('Restaurer mes achats'),
          ),
          const SizedBox(height: 8),
          Text(
            'Paiement sécurisé via Google Play',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: AppColors.textSecondary,
                ),
          ),
        ],
      ),
    );
  }

  Future<void> _purchase() async {
    if (_selectedProductId == null) return;

    setState(() => _isLoading = true);

    try {
      final purchaseService = ref.read(purchaseServiceProvider);
      PurchaseResult result;

      // Check if it's a subscription or credit pack
      final isSubscription = AvailableProducts.subscriptions
          .any((p) => p.id == _selectedProductId);

      if (isSubscription) {
        final isYearly = _selectedProductId!.contains('yearly');
        result = await purchaseService.subscribePremium(yearly: isYearly);
      } else {
        result = await purchaseService.purchaseAnimationPack(_selectedProductId!);
      }

      if (mounted) {
        if (result.success) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(result.message),
              backgroundColor: AppColors.success,
            ),
          );
          context.pop();
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(result.message),
              backgroundColor: AppColors.error,
            ),
          );
        }
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _restorePurchases() async {
    setState(() => _isLoading = true);

    try {
      final purchaseService = ref.read(purchaseServiceProvider);
      final result = await purchaseService.restorePurchases();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result.message),
            backgroundColor: result.success ? AppColors.success : AppColors.info,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }
}

class _FeatureBadge extends StatelessWidget {
  final IconData icon;
  final String label;

  const _FeatureBadge({
    required this.icon,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.primary.withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: AppColors.primary),
          const SizedBox(width: 6),
          Text(
            label,
            style: const TextStyle(
              color: AppColors.primary,
              fontWeight: FontWeight.w600,
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }
}

class _ProductCard extends StatelessWidget {
  final PurchaseProduct product;
  final bool isSelected;
  final String? badge;
  final Color? badgeColor;
  final VoidCallback onTap;

  const _ProductCard({
    required this.product,
    required this.isSelected,
    this.badge,
    this.badgeColor,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      child: Material(
        color: isSelected ? AppColors.primary.withOpacity(0.05) : AppColors.surfaceLight,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(16),
          child: Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: isSelected ? AppColors.primary : AppColors.divider,
                width: isSelected ? 2 : 1,
              ),
            ),
            child: Row(
              children: [
                // Selection indicator
                Container(
                  width: 24,
                  height: 24,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: isSelected ? AppColors.primary : AppColors.divider,
                      width: 2,
                    ),
                    color: isSelected ? AppColors.primary : Colors.transparent,
                  ),
                  child: isSelected
                      ? const Icon(Icons.check, size: 14, color: Colors.white)
                      : null,
                ),
                const SizedBox(width: 16),

                // Content
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            product.title,
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: FontWeight.bold,
                                ),
                          ),
                          if (badge != null) ...[
                            const SizedBox(width: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8,
                                vertical: 2,
                              ),
                              decoration: BoxDecoration(
                                color: badgeColor ?? AppColors.success,
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: Text(
                                badge!,
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 10,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                          ],
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        product.description,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: AppColors.textSecondary,
                            ),
                      ),
                    ],
                  ),
                ),

                // Price
                Text(
                  product.price,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: AppColors.primary,
                      ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
