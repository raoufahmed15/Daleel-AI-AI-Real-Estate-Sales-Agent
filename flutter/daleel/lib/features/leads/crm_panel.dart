import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/l10n.dart';
import '../../core/models.dart';
import '../../core/providers.dart';
import '../../core/widgets.dart';
import 'lead_detail_screen.dart' show crmProvider;

/// CRM sandbox view of one lead: stage, consent status, activity history, bookings, handoffs.
class CrmPanel extends ConsumerStatefulWidget {
  const CrmPanel({required this.crm});
  final Crm crm;
  @override
  ConsumerState<CrmPanel> createState() => _CrmPanelState();
}

class _CrmPanelState extends ConsumerState<CrmPanel> {
  final _note = TextEditingController();

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  void _refresh() => ref.invalidate(crmProvider(widget.crm.lead.id));

  Future<void> _newHandoff() async {
    String category = 'other';
    final reason = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setS) => AlertDialog(
          title: Text(context.tr('create_handoff')),
          content: SizedBox(
            width: 420,
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              NullableDropdown(label: context.tr('category'), value: category, options: kHandoffCategories, allowNull: false, onChanged: (v) => setS(() => category = v!)),
              const SizedBox(height: 12),
              TextField(controller: reason, maxLines: 3, decoration: InputDecoration(labelText: context.tr('reason'))),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(context.tr('cancel'))),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(context.tr('create'))),
          ],
        ),
      ),
    );
    if (ok == true && mounted) {
      final done = await runAction(context, () => ref.read(repoProvider).createHandoff({'lead_id': widget.crm.lead.id, 'category': category, 'reason': reason.text.trim()}), ok: context.tr('saved'));
      if (done) _refresh();
    }
    reason.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final crm = widget.crm;
    final l = crm.lead;
    final repo = ref.read(repoProvider);
    return ListView(children: [
      SectionCard(
        title: context.tr('funnel_stage'),
        child: Wrap(spacing: 16, runSpacing: 12, crossAxisAlignment: WrapCrossAlignment.center, children: [
          SizedBox(
            width: 240,
            child: NullableDropdown(
              label: context.tr('funnel_stage'),
              value: l.status,
              options: kLeadStatuses,
              allowNull: false,
              onChanged: (v) async {
                if (v != null && v != l.status && await runAction(context, () => repo.updateStage(l.id, v), ok: context.tr('saved'))) _refresh();
              },
            ),
          ),
          StatusChip(l.consentStatus, label: '${context.tr('consent_status')}: ${context.tr(l.consentStatus)}'),
          if (l.optedOut) StatusChip('denied', label: context.tr('opted_out')),
          StatusChip(crm.qualificationComplete ? 'granted' : 'medium', label: crm.qualificationComplete ? context.tr('qualification_complete') : '${context.tr('missing')}: ${crm.missing.map((m) => context.tr(m)).join(', ')}'),
          if (crm.openHandoffStatus != null) StatusChip(crm.openHandoffStatus!, label: '${context.tr('nav_handoffs')}: ${context.tr(crm.openHandoffStatus!)}'),
        ]),
      ),
      const SizedBox(height: 12),
      SectionCard(
        title: context.tr('activity_history'),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: TextField(controller: _note, decoration: InputDecoration(hintText: context.tr('add_note')))),
            const SizedBox(width: 8),
            FilledButton(
              onPressed: () async {
                final t = _note.text.trim();
                if (t.isEmpty) return;
                if (await runAction(context, () => repo.addNote(l.id, t))) {
                  _note.clear();
                  _refresh();
                }
              },
              child: Text(context.tr('add')),
            ),
          ]),
          const SizedBox(height: 8),
          for (final a in crm.activities)
            ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.circle, size: 10),
              title: Text(a.description),
              subtitle: Text('${fmtDate(a.createdAt)} · ${a.type} · ${a.actor}'),
            ),
        ]),
      ),
      const SizedBox(height: 12),
      SectionCard(
        title: context.tr('booking_history'),
        trailing: Text(context.tr('simulated'), style: TextStyle(color: Colors.amber.shade800, fontWeight: FontWeight.bold)),
        child: crm.bookings.isEmpty
            ? Text(context.tr('none'))
            : Column(children: [
                for (final b in crm.bookings)
                  ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    title: Text(b.propertyTitle),
                    subtitle: Text(fmtDate(b.start)),
                    trailing: StatusChip(b.status),
                  ),
              ]),
      ),
      const SizedBox(height: 12),
      SectionCard(
        title: context.tr('nav_handoffs'),
        trailing: TextButton.icon(onPressed: _newHandoff, icon: const Icon(Icons.add), label: Text(context.tr('create_handoff'))),
        child: crm.handoffs.isEmpty
            ? Text(context.tr('none'))
            : Column(children: [
                for (final h in crm.handoffs)
                  ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    title: Text(context.tr(h.category)),
                    subtitle: Text(h.reason),
                    trailing: StatusChip(h.status),
                  ),
              ]),
      ),
    ]);
  }
}
