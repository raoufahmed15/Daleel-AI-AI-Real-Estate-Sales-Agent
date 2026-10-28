import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';
import 'repository.dart';

String defaultBaseUrl() =>
    (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) ? 'http://10.0.2.2:8000' : 'http://localhost:8000';
String defaultRagBaseUrl() =>
    (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) ? 'http://10.0.2.2:8100' : 'http://localhost:8100';

final baseUrlProvider = StateProvider<String>((ref) => defaultBaseUrl());
final ragBaseUrlProvider = StateProvider<String>((ref) => defaultRagBaseUrl());
final apiProvider = Provider<ApiClient>((ref) => ApiClient(ref.watch(baseUrlProvider)));
final ragApiProvider = Provider<ApiClient>((ref) => ApiClient(
      ref.watch(ragBaseUrlProvider),
      timeout: const Duration(seconds: 150),
    ));
final repoProvider = Provider<Repository>((ref) => Repository(ref.watch(apiProvider), ref.watch(ragApiProvider)));
final localeProvider = StateProvider<Locale>((ref) => const Locale('en'));
final navIndexProvider = StateProvider<int>((ref) => 0);

final dashboardProvider = FutureProvider.autoDispose((ref) => ref.watch(repoProvider).dashboard());
final integrationsProvider = FutureProvider.autoDispose((ref) => ref.watch(repoProvider).integrations());
final settingsProvider = FutureProvider.autoDispose((ref) => ref.watch(repoProvider).settings());
