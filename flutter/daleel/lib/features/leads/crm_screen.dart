import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/l10n.dart';
import '../../core/models.dart';
import '../../core/widgets.dart';
import 'crm_panel.dart';
import 'lead_detail_screen.dart' show crmProvider;
import 'leads_screen.dart' show leadsProvider;

final crmSelectedLeadProvider = StateProvider<int?>((ref) => null);

/// CRM Sandbox: pick a lead and inspect/change its CRM record (persisted in the backend DB).
class CrmScreen extends ConsumerWidget {
  const CrmScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final leads = ref.watch(leadsProvider);
    final selected = ref.watch(crmSelectedLeadProvider);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      PageHeader(context.tr('nav_crm')),
      Banner2(context.tr('crm_sandbox_note')),
      const SizedBox(height: 12),
      AsyncBody<PageResult<Lead>>(
        value: leads,
        onRetry: () => ref.invalidate(leadsProvider),
        builder: (page) => DropdownButtonFormField<int>(
          initialValue: page.items.any((e) => e.id == selected) ? selected : null,
          isExpanded: true,
          decoration: InputDecoration(labelText: context.tr('select_lead')),
          items: [for (final l in page.items) DropdownMenuItem(value: l.id, child: Text('${l.name} · ${context.tr(l.status)}'))],
          onChanged: (v) => ref.read(crmSelectedLeadProvider.notifier).state = v,
        ),
      ),
      const SizedBox(height: 12),
      Expanded(
        child: selected == null
            ? Center(child: Text(context.tr('select_lead')))
            : AsyncBody<Crm>(
                value: ref.watch(crmProvider(selected)),
                onRetry: () => ref.invalidate(crmProvider(selected)),
                builder: (crm) => CrmPanel(crm: crm),
              ),
      ),
    ]);
  }
}
