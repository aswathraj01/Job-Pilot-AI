import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// App-wide design system — dark theme with indigo + cyan accent palette.
class AppTheme {
  // ── Color Palette ────────────────────────────────────────────────────────
  static const Color background = Color(0xFF0F172A);       // slate-900
  static const Color surface = Color(0xFF1E293B);          // slate-800
  static const Color surfaceVariant = Color(0xFF334155);   // slate-700
  static const Color primary = Color(0xFF6366F1);          // indigo-500
  static const Color primaryLight = Color(0xFF818CF8);     // indigo-400
  static const Color secondary = Color(0xFF22D3EE);        // cyan-400
  static const Color success = Color(0xFF10B981);          // emerald-500
  static const Color warning = Color(0xFFF59E0B);          // amber-500
  static const Color error = Color(0xFFEF4444);            // red-500
  static const Color textPrimary = Color(0xFFF1F5F9);      // slate-100
  static const Color textSecondary = Color(0xFF94A3B8);    // slate-400
  static const Color textMuted = Color(0xFF64748B);        // slate-500
  static const Color border = Color(0xFF1E293B);           // slate-800
  static const Color divider = Color(0xFF1E293B);

  // ── Status Colors ─────────────────────────────────────────────────────────
  static const Color statusSaved = Color(0xFF64748B);
  static const Color statusProcessing = Color(0xFF3B82F6);
  static const Color statusApplied = Color(0xFF6366F1);
  static const Color statusPhoneScreen = Color(0xFFF59E0B);
  static const Color statusInterview = Color(0xFF8B5CF6);
  static const Color statusOffer = Color(0xFF10B981);
  static const Color statusRejected = Color(0xFFEF4444);
  static const Color statusWithdrawn = Color(0xFF94A3B8);

  static Color statusColor(String status) {
    return switch (status) {
      'saved' => statusSaved,
      'processing' => statusProcessing,
      'applied' => statusApplied,
      'phone_screen' => statusPhoneScreen,
      'interview' => statusInterview,
      'offer' => statusOffer,
      'rejected' => statusRejected,
      'withdrawn' => statusWithdrawn,
      _ => statusSaved,
    };
  }

  static String statusLabel(String status) {
    return switch (status) {
      'saved' => 'Saved',
      'processing' => 'Processing',
      'applied' => 'Applied',
      'phone_screen' => 'Phone Screen',
      'interview' => 'Interview',
      'offer' => 'Offer',
      'rejected' => 'Rejected',
      'withdrawn' => 'Withdrawn',
      _ => status,
    };
  }

  // ── Dark Theme ────────────────────────────────────────────────────────────
  static ThemeData get darkTheme {
    final base = ThemeData.dark();
    final textTheme = GoogleFonts.interTextTheme(base.textTheme).copyWith(
      displayLarge: GoogleFonts.inter(fontSize: 36, fontWeight: FontWeight.w700, color: textPrimary),
      displayMedium: GoogleFonts.inter(fontSize: 28, fontWeight: FontWeight.w700, color: textPrimary),
      headlineLarge: GoogleFonts.inter(fontSize: 24, fontWeight: FontWeight.w600, color: textPrimary),
      headlineMedium: GoogleFonts.inter(fontSize: 20, fontWeight: FontWeight.w600, color: textPrimary),
      titleLarge: GoogleFonts.inter(fontSize: 18, fontWeight: FontWeight.w600, color: textPrimary),
      titleMedium: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.w500, color: textPrimary),
      bodyLarge: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.w400, color: textPrimary),
      bodyMedium: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w400, color: textSecondary),
      bodySmall: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w400, color: textMuted),
      labelLarge: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600, color: textPrimary),
    );

    return base.copyWith(
      scaffoldBackgroundColor: background,
      colorScheme: const ColorScheme.dark(
        primary: primary,
        secondary: secondary,
        surface: surface,
        error: error,
        onPrimary: Colors.white,
        onSecondary: background,
        onSurface: textPrimary,
        onError: Colors.white,
      ),
      textTheme: textTheme,
      appBarTheme: AppBarTheme(
        backgroundColor: background,
        elevation: 0,
        titleTextStyle: GoogleFonts.inter(fontSize: 18, fontWeight: FontWeight.w600, color: textPrimary),
        iconTheme: const IconThemeData(color: textSecondary),
      ),
      cardTheme: CardTheme(
        color: surface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: surfaceVariant.withOpacity(0.5), width: 1),
        ),
        margin: EdgeInsets.zero,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          textStyle: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: primary,
          side: const BorderSide(color: primary),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surfaceVariant.withOpacity(0.4),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: surfaceVariant),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: surfaceVariant),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: primary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: error),
        ),
        hintStyle: GoogleFonts.inter(color: textMuted, fontSize: 14),
        labelStyle: GoogleFonts.inter(color: textSecondary, fontSize: 14),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
      dividerTheme: const DividerThemeData(color: divider, thickness: 1),
      chipTheme: ChipThemeData(
        backgroundColor: surfaceVariant.withOpacity(0.5),
        labelStyle: GoogleFonts.inter(fontSize: 12, color: textSecondary),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
        side: BorderSide.none,
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: surfaceVariant,
        contentTextStyle: GoogleFonts.inter(color: textPrimary, fontSize: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }
}

/// Gradient builder for hero sections and cards.
class AppGradients {
  static const LinearGradient primaryGradient = LinearGradient(
    colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
    begin: Alignment.centerLeft,
    end: Alignment.centerRight,
  );

  static const LinearGradient backgroundGradient = LinearGradient(
    colors: [Color(0xFF0F172A), Color(0xFF1E1B4B)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient successGradient = LinearGradient(
    colors: [Color(0xFF10B981), Color(0xFF059669)],
    begin: Alignment.centerLeft,
    end: Alignment.centerRight,
  );
}
