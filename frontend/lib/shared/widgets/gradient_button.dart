import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// Gradient-filled primary action button.
class GradientButton extends StatelessWidget {
  final VoidCallback? onPressed;
  final Widget child;
  final bool isLoading;
  final double height;

  const GradientButton({
    super.key,
    required this.onPressed,
    required this.child,
    this.isLoading = false,
    this.height = 52,
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedOpacity(
      opacity: onPressed == null ? 0.6 : 1.0,
      duration: const Duration(milliseconds: 200),
      child: Container(
        height: height,
        decoration: BoxDecoration(
          gradient: onPressed == null ? null : AppGradients.primaryGradient,
          color: onPressed == null ? AppTheme.surfaceVariant : null,
          borderRadius: BorderRadius.circular(10),
          boxShadow: onPressed != null
              ? [BoxShadow(color: AppTheme.primary.withOpacity(0.35), blurRadius: 16, offset: const Offset(0, 4))]
              : null,
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: isLoading ? null : onPressed,
            borderRadius: BorderRadius.circular(10),
            child: Center(
              child: isLoading
                  ? const SizedBox(
                      width: 22,
                      height: 22,
                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.5),
                    )
                  : DefaultTextStyle(
                      style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600),
                      child: child,
                    ),
            ),
          ),
        ),
      ),
    );
  }
}
