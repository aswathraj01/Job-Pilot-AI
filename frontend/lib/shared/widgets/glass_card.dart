import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// Glassmorphism card widget with blur effect and subtle border.
class GlassCard extends StatelessWidget {
  final Widget child;
  final EdgeInsets? padding;
  final double borderRadius;
  final Color? color;

  const GlassCard({
    super.key,
    required this.child,
    this.padding,
    this.borderRadius = 16,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding ?? const EdgeInsets.all(32),
      decoration: BoxDecoration(
        color: color ?? AppTheme.surface.withOpacity(0.9),
        borderRadius: BorderRadius.circular(borderRadius),
        border: Border.all(color: AppTheme.surfaceVariant.withOpacity(0.5)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.3),
            blurRadius: 32,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: child,
    );
  }
}
