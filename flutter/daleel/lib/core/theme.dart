import 'package:flutter/material.dart';

const _gold = Color(0xFFC99A62);
const _cream = Color(0xFFF2E8DA);
const _background = Color(0xFF0D0B09);
const _surface = Color(0xFF171411);
const _surfaceRaised = Color(0xFF211B16);
const _outline = Color(0xFF514333);

ThemeData buildTheme() {
  final scheme = ColorScheme(
    brightness: Brightness.dark,
    primary: _gold,
    onPrimary: _background,
    secondary: const Color(0xFFE1C49F),
    onSecondary: _background,
    error: const Color(0xFFE57373),
    onError: _background,
    surface: _surface,
    onSurface: _cream,
    surfaceContainerHighest: _surfaceRaised,
    onSurfaceVariant: const Color(0xFFC2B6A7),
    outline: _outline,
    outlineVariant: const Color(0xFF382F26),
    shadow: Colors.black,
    scrim: Colors.black,
    inverseSurface: _cream,
    onInverseSurface: _background,
    inversePrimary: const Color(0xFF805A30),
    surfaceTint: _gold,
  );
  return ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    colorScheme: scheme,
    scaffoldBackgroundColor: _background,
    canvasColor: _surface,
    dividerColor: _outline.withValues(alpha: .55),
    appBarTheme: const AppBarTheme(
      backgroundColor: _background,
      foregroundColor: _cream,
      centerTitle: false,
      elevation: 0,
      scrolledUnderElevation: 0,
    ),
    cardTheme: CardThemeData(
      color: _surface,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(color: _outline.withValues(alpha: .45)),
      ),
    ),
    drawerTheme: const DrawerThemeData(
      backgroundColor: _surface,
      surfaceTintColor: Colors.transparent,
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: _surface,
      indicatorColor: _gold.withValues(alpha: .16),
      elevation: 0,
      labelTextStyle: WidgetStateProperty.resolveWith((states) => TextStyle(
            color: states.contains(WidgetState.selected)
                ? _gold
                : const Color(0xFF988B7B),
            fontSize: 11,
            fontWeight: states.contains(WidgetState.selected)
                ? FontWeight.w600
                : FontWeight.w400,
          )),
      iconTheme: WidgetStateProperty.resolveWith((states) => IconThemeData(
            color: states.contains(WidgetState.selected)
                ? _gold
                : const Color(0xFF988B7B),
          )),
    ),
    navigationRailTheme: NavigationRailThemeData(
      backgroundColor: _background,
      selectedIconTheme: const IconThemeData(color: _gold),
      unselectedIconTheme: const IconThemeData(color: Color(0xFF988B7B)),
      selectedLabelTextStyle: const TextStyle(color: _gold),
      unselectedLabelTextStyle: const TextStyle(color: Color(0xFF988B7B)),
      indicatorColor: _gold.withValues(alpha: .16),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: _surfaceRaised,
      isDense: true,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: BorderSide(color: _outline.withValues(alpha: .65)),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: BorderSide(color: _outline.withValues(alpha: .65)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: _gold, width: 1.4),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: _gold,
        foregroundColor: _background,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(foregroundColor: _gold),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: _surfaceRaised,
      selectedColor: _gold.withValues(alpha: .18),
      side: BorderSide(color: _outline.withValues(alpha: .7)),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      labelStyle: const TextStyle(color: _cream),
    ),
    iconTheme: const IconThemeData(color: _gold),
    textTheme: Typography.material2021().white.apply(
          bodyColor: _cream,
          displayColor: _cream,
          fontFamily: 'Roboto',
        ),
  );
}

Color statusColor(String v) {
  switch (v) {
    case 'won':
    case 'available':
    case 'granted':
    case 'resolved':
    case 'integrated':
      return Colors.green;
    case 'lost':
    case 'sold':
    case 'denied':
    case 'cancelled':
    case 'dismissed':
    case 'high':
      return Colors.red;
    case 'reserved':
    case 'in_review':
    case 'negotiation':
    case 'medium':
    case 'unknown':
      return Colors.orange;
    case 'not_implemented':
    case 'not_configured':
      return Colors.blueGrey;
    default:
      return Colors.teal;
  }
}
