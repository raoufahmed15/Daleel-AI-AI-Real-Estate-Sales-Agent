import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';
import 'repository.dart';

String defaultBaseUrl() =>
    (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) ? 'http://10.0.2.2:8000' : 'http://localhost:8000';

final baseUrlProvider = StateProvider<String>((ref) => defaultBaseUrl());
final apiProvider = Provider<ApiClient>((ref) => ApiClient(ref.watch(baseUrlProvider)));
final repoProvider = Provider<Repository>((ref) => Repository(ref.watch(apiProvider)));
final localeProvider = StateProvider<Locale>((ref) => const Locale('en'));
final navIndexProvider = StateProvider<int>((ref) => 0);

final dashboardProvider = FutureProvider.autoDispose((ref) => ref.watch(repoProvider).dashboard());
final integrationsProvider = FutureProvider.autoDispose((ref) => ref.watch(repoProvider).integrations());
final settingsProvider = FutureProvider.autoDispose((ref) => ref.watch(repoProvider).settings());
