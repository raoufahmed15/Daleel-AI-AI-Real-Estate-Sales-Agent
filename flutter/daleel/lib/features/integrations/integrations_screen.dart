import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/l10n.dart';
import '../../core/providers.dart';
import '../../core/widgets.dart';

class IntegrationsScreen extends ConsumerWidget {
  const IntegrationsScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AsyncBody<Map<String, dynamic>>(
      value: ref.watch(integrationsProvider),
      onRetry: () => ref.invalidate(integrationsProvider),
      builder: (d) {
        final modules = (d['modules'] as List).cast<Map<String, dynamic>>();
        return ListView(children: [
          PageHeader(context.tr('nav_integrations')),
          Banner2(context.tr('integration_note')),
          const SizedBox(height: 12),
          for (final m in modules) ...[
            SectionCard(
              title: m['title'] as String,
              trailing: StatusChip(m['status'] as String, label: m['status'] == 'integrated' ? context.tr('integrated') : context.tr('not_integrated')),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(m['description'] as String),
                const SizedBox(height: 8),
                InfoRow(context.tr('endpoint'), m['endpoint'] as String),
                InfoRow(context.tr('status'), m['status'] as String),
                InfoRow(context.tr('integration_slot'), m['integration_slot'] as String),
              ]),
            ),
            const SizedBox(height: 12),
          ],
        ]);
      },
    );
  }
}
