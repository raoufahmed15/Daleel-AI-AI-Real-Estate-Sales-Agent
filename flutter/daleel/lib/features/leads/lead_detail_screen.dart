import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/l10n.dart';
import '../../core/models.dart';
import '../../core/providers.dart';
import '../../core/widgets.dart';
import 'crm_panel.dart';
import 'lead_form_screen.dart';

final crmProvider = FutureProvider.autoDispose.family<Crm, int>((ref, id) => ref.watch(repoProvider).crm(id));

class LeadDetailScreen extends ConsumerWidget {
  const LeadDetailScreen({required this.leadId});
  final int leadId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final crm = ref.watch(crmProvider(leadId));
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: Text(crm.valueOrNull?.lead.name ?? context.tr('nav_leads')),
          actions: [
            if (crm.hasValue)
              IconButton(
                icon: const Icon(Icons.edit),
                tooltip: context.tr('edit_lead'),
                onPressed: () async {
                  await Navigator.push(context, MaterialPageRoute(builder: (_) => LeadFormScreen(lead: crm.value!.lead)));
                  ref.invalidate(crmProvider(leadId));
                },
              ),
          ],
          bottom: TabBar(tabs: [Tab(text: context.tr('details')), Tab(text: context.tr('nav_crm'))]),
        ),
        body: AsyncBody<Crm>(
          value: crm,
          onRetry: () => ref.invalidate(crmProvider(leadId)),
          builder: (data) => TabBarView(children: [
            Padding(padding: const EdgeInsets.all(16), child: _DetailsTab(crm: data)),
            Padding(padding: const EdgeInsets.all(16), child: CrmPanel(crm: data)),
          ]),
        ),
      ),
    );
  }
}

class _DetailsTab extends ConsumerWidget {
  const _DetailsTab({required this.crm});
  final Crm crm;

  Future<void> _followUps(BuildContext context, WidgetRef ref) async {
    try {
      final r = await ref.read(repoProvider).followUps(crm.lead.id);
      if (!context.mounted) return;
      final list = (r['suggestions'] as List).cast<Map<String, dynamic>>();
      await showDialog<void>(
        context: context,
        builder: (_) => AlertDialog(
          title: Text(context.tr('follow_up_suggestions')),
          content: SizedBox(
            width: 480,
            child: ListView(shrinkWrap: true, children: [
              Banner2(context.tr('follow_up_note')),
              if (r['warning'] != null) ...[const SizedBox(height: 8), Banner2(context.tr('consent_unknown_warning'), icon: Icons.warning_amber)],
              for (final s in list) ListTile(title: Text(s['text'] as String), subtitle: Text(s['reason'] as String)),
            ]),
          ),
          actions: [TextButton(onPressed: () => Navigator.pop(context), child: Text(context.tr('close')))],
        ),
      );
    } on ApiException catch (e) {
      if (context.mounted) {
        await showDialog<void>(
          context: context,
          builder: (_) => AlertDialog(
            icon: const Icon(Icons.block, color: Colors.red),
            title: Text(context.tr('follow_up_blocked')),
            content: Text(e.message),
            actions: [TextButton(onPressed: () => Navigator.pop(context), child: Text(context.tr('close')))],
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = crm.lead;
    final repo = ref.read(repoProvider);
    void refresh() => ref.invalidate(crmProvider(l.id));
    return ListView(children: [
      SectionCard(
        title: context.tr('profile'),
        child: Column(children: [
          InfoRow(context.tr('phone'), orNotProvided(context, l.phone)),
          InfoRow(context.tr('email'), orNotProvided(context, l.email)),
          InfoRow(context.tr('status'), context.tr(l.status)),
          InfoRow(context.tr('priority'), context.tr(l.priority)),
        ]),
      ),
      const SizedBox(height: 12),
      SectionCard(
        title: context.tr('qualification'),
        child: Column(children: [
          InfoRow(context.tr('budget'), fmtMoney(context, l.budget)),
          InfoRow(context.tr('preferred_location'), orNotProvided(context, l.preferredLocation)),
          InfoRow(context.tr('property_type'), l.propertyType == null ? context.tr('not_provided') : context.tr(l.propertyType!)),
          InfoRow(context.tr('down_payment'), fmtMoney(context, l.downPayment)),
          InfoRow(context.tr('monthly_installment'), fmtMoney(context, l.monthlyInstallment)),
          InfoRow(context.tr('purchase_timeline'), l.purchaseTimeline == null ? context.tr('not_provided') : context.tr(l.purchaseTimeline!)),
        ]),
      ),
      const SizedBox(height: 12),
      SectionCard(
        title: context.tr('consent'),
        child: Column(children: [
          NullableDropdown(
            label: context.tr('consent_status'),
            value: l.consentStatus,
            options: const ['unknown', 'granted', 'denied'],
            allowNull: false,
            onChanged: (v) async {
              if (v != null && await runAction(context, () => repo.updateConsent(l.id, {'consent_status': v}), ok: context.tr('saved'))) refresh();
            },
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(context.tr('opted_out')),
            subtitle: Text(context.tr('opt_out_hint')),
            value: l.optedOut,
            onChanged: (v) async {
              if (await runAction(context, () => repo.updateConsent(l.id, {'opted_out': v}), ok: context.tr('saved'))) refresh();
            },
          ),
        ]),
      ),
      const SizedBox(height: 12),
      SectionCard(
        title: context.tr('conversation_summary'),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(orNotProvided(context, l.conversationSummary)),
          const SizedBox(height: 8),
          Text(context.tr('next_steps'), style: Theme.of(context).textTheme.bodySmall),
          Text(orNotProvided(context, l.nextSteps)),
        ]),
      ),
      const SizedBox(height: 12),
      Align(
        alignment: AlignmentDirectional.centerStart,
        child: OutlinedButton.icon(
          onPressed: () => _followUps(context, ref),
          icon: const Icon(Icons.lightbulb_outline),
          label: Text(context.tr('follow_up_suggestions')),
        ),
      ),
    ]);
  }
}
