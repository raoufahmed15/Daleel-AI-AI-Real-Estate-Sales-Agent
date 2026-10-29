import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../core/l10n.dart';
import '../../core/providers.dart';
import '../../core/widgets.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});
  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  late final url = TextEditingController(text: ref.read(baseUrlProvider));
  late final ragUrl = TextEditingController(text: ref.read(ragBaseUrlProvider));

  @override
  void dispose() {
    url.dispose();
    ragUrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final locale = ref.watch(localeProvider);
    final settings = ref.watch(settingsProvider);
    return ListView(children: [
      PageHeader(context.tr('nav_settings')),
      SectionCard(
        title: context.tr('language'),
        child: SegmentedButton<String>(
          segments: const [ButtonSegment(value: 'en', label: Text('English')), ButtonSegment(value: 'ar', label: Text('العربية'))],
          selected: {locale.languageCode},
          onSelectionChanged: (s) => ref.read(localeProvider.notifier).state = Locale(s.first),
        ),
      ),
      const SizedBox(height: 12),
      SectionCard(
        title: context.tr('backend_url'),
        child: Row(children: [
          Expanded(child: TextField(controller: url, decoration: const InputDecoration(hintText: 'http://localhost:8000'))),
          const SizedBox(width: 8),
          FilledButton(
            onPressed: () {
              ref.read(baseUrlProvider.notifier).state = url.text.trim().replaceAll(RegExp(r'/+$'), '');
              ref.invalidate(settingsProvider);
              ref.invalidate(dashboardProvider);
              snack(context, context.tr('saved'));
            },
            child: Text(context.tr('save')),
          ),
        ]),
      ),
      const SizedBox(height: 12),
      SectionCard(
        title: context.tr('rag_url'),
        child: Row(children: [
          Expanded(
            child: TextField(
              controller: ragUrl,
              decoration: const InputDecoration(hintText: 'http://localhost:8100'),
            ),
          ),
          const SizedBox(width: 8),
          FilledButton(
            onPressed: () async {
              final value =
                  ragUrl.text.trim().replaceAll(RegExp(r'/+$'), '');
              final savedMessage = context.tr('saved');
              final saveFailedMessage = context.tr('save_failed');
              final messenger = ScaffoldMessenger.of(context);
              final errorColor = Theme.of(context).colorScheme.error;
              try {
                final preferences = await SharedPreferences.getInstance();
                await preferences.setString('rag_base_url', value);
                if (!mounted) return;
                ref.read(ragBaseUrlProvider.notifier).state = value;
                messenger.showSnackBar(
                  SnackBar(content: Text(savedMessage)),
                );
              } catch (error) {
                if (mounted) {
                  messenger.showSnackBar(
                    SnackBar(
                      content: Text('$saveFailedMessage: $error'),
                      backgroundColor: errorColor,
                    ),
                  );
                }
              }
            },
            child: Text(context.tr('save')),
          ),
        ]),
      ),
      const SizedBox(height: 12),
      AsyncBody<Map<String, dynamic>>(
        value: settings,
        onRetry: () => ref.invalidate(settingsProvider),
        builder: (s) {
          final db = s['database'] as Map<String, dynamic>;
          final mods = (s['modules'] as List).cast<Map<String, dynamic>>();
          final hf = (s['future_huggingface_integration_points'] as List).cast<Map<String, dynamic>>();
          return Column(children: [
            SectionCard(
              title: context.tr('application'),
              child: Column(children: [
                InfoRow(context.tr('app_mode'), '${s['app_mode']}'),
                InfoRow(context.tr('version'), '${s['version']}'),
                InfoRow(context.tr('database'), '${db['dialect']} · ${db['status']}'),
                InfoRow(context.tr('backend'), db['status'] == 'connected' ? context.tr('connected') : context.tr('unavailable')),
                InfoRow(context.tr('external_ai'), s['external_ai_calls_enabled'] == true ? context.tr('yes') : context.tr('disabled')),
                const SizedBox(height: 8),
                Banner2(s['notice'] as String),
              ]),
            ),
            const SizedBox(height: 12),
            SectionCard(
              title: context.tr('module_status'),
              child: Column(children: [
                for (final m in mods)
                  ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    title: Text(m['title'] as String),
                    trailing: StatusChip(m['status'] as String, label: m['status'] == 'integrated' ? context.tr('integrated') : context.tr('not_integrated')),
                  ),
              ]),
            ),
            const SizedBox(height: 12),
            SectionCard(
              title: context.tr('hf_points'),
              child: Column(children: [
                for (final h in hf) ListTile(dense: true, contentPadding: EdgeInsets.zero, title: Text(h['name'] as String), subtitle: Text(h['note'] as String), trailing: Text(context.tr('reserved'))),
              ]),
            ),
          ]);
        },
      ),
    ]);
  }
}
