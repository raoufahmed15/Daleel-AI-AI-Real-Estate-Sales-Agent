import 'package:flutter/material.dart';

const seed = Color(0xFF0F766E);

ThemeData buildTheme(Brightness b) => ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(seedColor: seed, brightness: b),
      inputDecorationTheme: const InputDecorationTheme(border: OutlineInputBorder(), isDense: true),
    );

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
