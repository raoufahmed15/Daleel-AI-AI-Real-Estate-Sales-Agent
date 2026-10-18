import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/l10n.dart';
import '../../core/providers.dart';
import '../../core/widgets.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AsyncBody<Map<String, dynamic>>(
      value: ref.watch(dashboardProvider),
      onRetry: () => ref.invalidate(dashboardProvider),
      builder: (d) {
        final c = d['calculated'] as Map<String, dynamic>;
        final byStatus = c['leads_by_status'] as Map<String, dynamic>;
        final total = (c['leads_total'] as int);
        final ai = (d['unavailable_ai_metrics'] as List).cast<Map<String, dynamic>>();
        return RefreshIndicator(
          onRefresh: () async => ref.refresh(dashboardProvider.future),
          child: ListView(children: [
            PageHeader(context.tr('nav_dashboard'), actions: [
              IconButton(onPressed: () => ref.invalidate(dashboardProvider), icon: const Icon(Icons.refresh)),
            ]),
            Text(context.tr('calculated_metrics'), style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 8),
            Wrap(spacing: 12, runSpacing: 12, children: [
              MetricCard(label: context.tr('total_leads'), value: '${c['leads_total']}', icon: Icons.people),
              MetricCard(label: context.tr('available_properties'), value: '${c['properties_available']}', icon: Icons.apartment),
              MetricCard(label: context.tr('upcoming_viewings'), value: '${c['bookings_upcoming']}', icon: Icons.event),
              MetricCard(label: context.tr('pending_handoffs'), value: '${c['handoffs_pending']}', icon: Icons.support_agent),
              MetricCard(label: context.tr('bookings_scheduled'), value: '${c['bookings_scheduled_total']}', icon: Icons.event_available),
              MetricCard(label: context.tr('bookings_cancelled'), value: '${c['bookings_cancelled']}', icon: Icons.event_busy),
              MetricCard(label: context.tr('crm_activities'), value: '${c['crm_activities_total']}', icon: Icons.history),
              MetricCard(label: context.tr('fully_qualified'), value: '${c['leads_fully_qualified']}', icon: Icons.fact_check),
              MetricCard(label: context.tr('opted_out'), value: '${c['leads_opted_out']}', icon: Icons.block),
            ]),
            const SizedBox(height: 16),
            SectionCard(
              title: context.tr('leads_by_status'),
              child: Column(children: [
                for (final e in byStatus.entries)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Row(children: [
                      SizedBox(width: 130, child: Text(context.tr(e.key))),
                      Expanded(child: LinearProgressIndicator(value: total == 0 ? 0 : (e.value as int) / total, minHeight: 8)),
                      SizedBox(width: 36, child: Text('${e.value}', textAlign: TextAlign.end)),
                    ]),
                  ),
              ]),
            ),
            const SizedBox(height: 16),
            SectionCard(
              title: context.tr('ai_metrics_unavailable'),
              child: Column(children: [
                for (final m in ai)
                  ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.lock_outline),
                    title: Text(m['name'] as String),
                    trailing: StatusChip(m['status'] as String, label: context.tr('not_integrated')),
                  ),
                Text(context.tr('ai_metrics_note'), style: Theme.of(context).textTheme.bodySmall),
              ]),
            ),
          ]),
        );
      },
    );
  }
}
