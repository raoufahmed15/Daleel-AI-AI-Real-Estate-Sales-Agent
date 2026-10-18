import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/l10n.dart';
import '../../core/models.dart';
import '../../core/providers.dart';
import '../../core/widgets.dart';

final handoffStatusFilterProvider = StateProvider<String?>((ref) => null);

final handoffsProvider = FutureProvider.autoDispose<List<Handoff>>(
    (ref) => ref.watch(repoProvider).handoffs(status: ref.watch(handoffStatusFilterProvider)));

final handoffProvider = FutureProvider.autoDispose.family<Handoff, int>((ref, id) => ref.watch(repoProvider).handoff(id));

const _transitions = {
  'open': ['in_review', 'resolved', 'dismissed'],
  'in_review': ['open', 'resolved', 'dismissed'],
  'resolved': ['open'],
  'dismissed': ['open'],
};

class HandoffsScreen extends ConsumerWidget {
  const HandoffsScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filter = ref.watch(handoffStatusFilterProvider);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      PageHeader(context.tr('nav_handoffs'), actions: [
        FilledButton.icon(
          icon: const Icon(Icons.add),
          label: Text(context.tr('create_handoff')),
          onPressed: () async {
            final ok = await showDialog<bool>(context: context, builder: (_) => const _NewHandoffDialog());
            if (ok == true) {
              ref.invalidate(handoffsProvider);
              ref.invalidate(dashboardProvider);
            }
          },
        ),
      ]),
      Wrap(spacing: 8, children: [
        ChoiceChip(label: Text(context.tr('all')), selected: filter == null, onSelected: (_) => ref.read(handoffStatusFilterProvider.notifier).state = null),
        for (final s in kHandoffStatuses)
          ChoiceChip(label: Text(context.tr(s)), selected: filter == s, onSelected: (_) => ref.read(handoffStatusFilterProvider.notifier).state = s),
      ]),
      const SizedBox(height: 12),
      Expanded(
        child: AsyncBody<List<Handoff>>(
          value: ref.watch(handoffsProvider),
          onRetry: () => ref.invalidate(handoffsProvider),
          builder: (list) {
            if (list.isEmpty) return Center(child: Text(context.tr('no_results')));
            return ListView.separated(
              itemCount: list.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (_, i) {
                final h = list[i];
                return ListTile(
                  leading: const Icon(Icons.support_agent),
                  title: Text('#${h.id} · ${context.tr(h.category)}'),
                  subtitle: Text('${h.leadName ?? context.tr('no_lead')} · ${h.reason}', maxLines: 2, overflow: TextOverflow.ellipsis),
                  trailing: StatusChip(h.status),
                  onTap: () async {
                    await showDialog<void>(context: context, builder: (_) => _HandoffDetailDialog(handoffId: h.id));
                    ref.invalidate(handoffsProvider);
                    ref.invalidate(dashboardProvider);
                  },
                );
              },
            );
          },
        ),
      ),
    ]);
  }
}

class _HandoffDetailDialog extends ConsumerStatefulWidget {
  const _HandoffDetailDialog({required this.handoffId});
  final int handoffId;
  @override
  ConsumerState<_HandoffDetailDialog> createState() => _HandoffDetailDialogState();
}

class _HandoffDetailDialogState extends ConsumerState<_HandoffDetailDialog> {
  final note = TextEditingController();
  final assignee = TextEditingController();

  @override
  void dispose() {
    note.dispose();
    assignee.dispose();
    super.dispose();
  }

  Future<void> _update(Map<String, dynamic> body) async {
    if (await runAction(context, () => ref.read(repoProvider).updateHandoff(widget.handoffId, body), ok: context.tr('saved'))) {
      note.clear();
      ref.invalidate(handoffProvider(widget.handoffId));
    }
  }

  @override
  Widget build(BuildContext context) {
    final value = ref.watch(handoffProvider(widget.handoffId));
    return AlertDialog(
      title: Text('${context.tr('nav_handoffs')} #${widget.handoffId}'),
      content: SizedBox(
        width: 560,
        child: AsyncBody<Handoff>(
          value: value,
          onRetry: () => ref.invalidate(handoffProvider(widget.handoffId)),
          builder: (h) => SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              InfoRow(context.tr('category'), context.tr(h.category)),
              InfoRow(context.tr('lead'), h.leadName ?? context.tr('no_lead')),
              InfoRow(context.tr('reason'), h.reason),
              InfoRow(context.tr('assigned_to'), orNotProvided(context, h.assignedTo)),
              Row(children: [
                Text(context.tr('status'), style: Theme.of(context).textTheme.bodySmall),
                const SizedBox(width: 12),
                StatusChip(h.status),
              ]),
              const SizedBox(height: 8),
              Wrap(spacing: 8, children: [
                for (final s in _transitions[h.status] ?? const <String>[])
                  OutlinedButton(onPressed: () => _update({'status': s}), child: Text('→ ${context.tr(s)}')),
              ]),
              const SizedBox(height: 12),
              Row(children: [
                Expanded(child: TextField(controller: assignee, decoration: InputDecoration(labelText: context.tr('assigned_to')))),
                const SizedBox(width: 8),
                FilledButton(
                  onPressed: () {
                    final a = assignee.text.trim();
                    if (a.isNotEmpty) _update({'assigned_to': a});
                  },
                  child: Text(context.tr('assign')),
                ),
              ]),
              const SizedBox(height: 8),
              Row(children: [
                Expanded(child: TextField(controller: note, decoration: InputDecoration(labelText: context.tr('add_note')))),
                const SizedBox(width: 8),
                FilledButton(
                  onPressed: () {
                    final n = note.text.trim();
                    if (n.isNotEmpty) _update({'note': n});
                  },
                  child: Text(context.tr('add')),
                ),
              ]),
              const Divider(height: 24),
              Text(context.tr('activity_history'), style: Theme.of(context).textTheme.titleSmall),
              for (final e in h.events)
                ListTile(dense: true, contentPadding: EdgeInsets.zero, title: Text(e.description), subtitle: Text('${fmtDate(e.createdAt)} · ${e.type}')),
            ]),
          ),
        ),
      ),
      actions: [TextButton(onPressed: () => Navigator.pop(context), child: Text(context.tr('close')))],
    );
  }
}

class _NewHandoffDialog extends ConsumerStatefulWidget {
  const _NewHandoffDialog();
  @override
  ConsumerState<_NewHandoffDialog> createState() => _NewHandoffDialogState();
}

class _NewHandoffDialogState extends ConsumerState<_NewHandoffDialog> {
  List<Lead> leads = [];
  int? leadId;
  String category = 'other';
  final reason = TextEditingController();

  @override
  void initState() {
    super.initState();
    ref.read(repoProvider).leads().then((p) {
      if (mounted) setState(() => leads = p.items);
    }).catchError((_) {});
  }

  @override
  void dispose() {
    reason.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: Text(context.tr('create_handoff')),
        content: SizedBox(
          width: 460,
          child: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              DropdownButtonFormField<int?>(
                initialValue: leadId,
                isExpanded: true,
                decoration: InputDecoration(labelText: context.tr('lead')),
                items: [DropdownMenuItem<int?>(value: null, child: Text(context.tr('no_lead'))), for (final l in leads) DropdownMenuItem<int?>(value: l.id, child: Text(l.name))],
                onChanged: (v) => setState(() => leadId = v),
              ),
              const SizedBox(height: 12),
              NullableDropdown(label: context.tr('category'), value: category, options: kHandoffCategories, allowNull: false, onChanged: (v) => setState(() => category = v!)),
              const SizedBox(height: 12),
              TextField(controller: reason, maxLines: 3, decoration: InputDecoration(labelText: context.tr('reason'))),
            ]),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: Text(context.tr('cancel'))),
          FilledButton(
            onPressed: () async {
              final ok = await runAction(context, () => ref.read(repoProvider).createHandoff({'lead_id': leadId, 'category': category, 'reason': reason.text.trim()}), ok: context.tr('saved'));
              if (ok && context.mounted) Navigator.pop(context, true);
            },
            child: Text(context.tr('create')),
          ),
        ],
      );
}
