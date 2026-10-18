import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/l10n.dart';
import '../../core/models.dart';
import '../../core/providers.dart';
import '../../core/widgets.dart';

final bookingFilterProvider =
    StateProvider<String>((ref) => 'upcoming'); // upcoming | all | cancelled

final bookingsProvider = FutureProvider.autoDispose<List<Booking>>((ref) {
  final f = ref.watch(bookingFilterProvider);
  final repo = ref.watch(repoProvider);
  if (f == 'upcoming') return repo.bookings(upcoming: true);
  if (f == 'cancelled') return repo.bookings(status: 'cancelled');
  return repo.bookings();
});

class BookingsScreen extends ConsumerWidget {
  const BookingsScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filter = ref.watch(bookingFilterProvider);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      PageHeader(context.tr('nav_bookings'), actions: [
        FilledButton.icon(
          icon: const Icon(Icons.add),
          label: Text(context.tr('new_booking')),
          onPressed: () async {
            final created = await showDialog<bool>(
                context: context, builder: (_) => const NewBookingDialog());
            if (created == true) {
              ref.invalidate(bookingsProvider);
              ref.invalidate(dashboardProvider);
            }
          },
        ),
      ]),
      Banner2(context.tr('simulated_banner'), icon: Icons.science_outlined),
      const SizedBox(height: 12),
      SegmentedButton<String>(
        segments: [
          ButtonSegment(value: 'upcoming', label: Text(context.tr('upcoming'))),
          ButtonSegment(value: 'all', label: Text(context.tr('all'))),
          ButtonSegment(
              value: 'cancelled', label: Text(context.tr('cancelled'))),
        ],
        selected: {filter},
        onSelectionChanged: (s) =>
            ref.read(bookingFilterProvider.notifier).state = s.first,
      ),
      const SizedBox(height: 12),
      Expanded(
        child: AsyncBody<List<Booking>>(
          value: ref.watch(bookingsProvider),
          onRetry: () => ref.invalidate(bookingsProvider),
          builder: (list) {
            if (list.isEmpty)
              return Center(child: Text(context.tr('no_results')));
            return ListView.separated(
              itemCount: list.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (_, i) {
                final b = list[i];
                return ListTile(
                  leading: const Icon(Icons.event),
                  title: Text('${fmtDate(b.start)} · ${b.propertyTitle}'),
                  subtitle: Text(
                      '${b.leadName} · ${context.tr('simulated')}${b.cancelReason == null ? '' : ' · ${b.cancelReason}'}'),
                  trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                    StatusChip(b.status),
                    if (b.status == 'scheduled')
                      IconButton(
                        tooltip: context.tr('cancel_booking'),
                        icon: const Icon(Icons.cancel_outlined),
                        onPressed: () async {
                          if (!await confirm(
                              context, context.tr('confirm_cancel_booking')))
                            return;
                          if (!context.mounted) return;
                          if (await runAction(context,
                              () => ref.read(repoProvider).cancelBooking(b.id),
                              ok: context.tr('saved'))) {
                            ref.invalidate(bookingsProvider);
                            ref.invalidate(dashboardProvider);
                          }
                        },
                      ),
                  ]),
                );
              },
            );
          },
        ),
      ),
    ]);
  }
}

class NewBookingDialog extends ConsumerStatefulWidget {
  const NewBookingDialog({super.key});
  @override
  ConsumerState<NewBookingDialog> createState() => _NewBookingDialogState();
}

class _NewBookingDialogState extends ConsumerState<NewBookingDialog> {
  List<Lead> leads = [];
  List<Property> props = [];
  int? leadId;
  int? propertyId;
  DateTime day = DateTime.now().add(const Duration(days: 1));
  List<Slot> slots = [];
  DateTime? chosen;
  bool loading = true;
  String? loadError;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final repo = ref.read(repoProvider);
      final l = await repo.leads();
      final p = await repo.properties({'availability': 'available'});
      if (!mounted) return;
      setState(() {
        leads = l.items;
        props = p.items;
        loading = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          loadError = e.toString();
          loading = false;
        });
      }
    }
  }

  String get _dayStr => day.toIso8601String().substring(0, 10);

  Future<void> _loadSlots() async {
    if (propertyId == null) return;
    chosen = null;
    try {
      final s =
          await ref.read(repoProvider).slots(propertyId!, _dayStr, leadId);
      if (mounted) setState(() => slots = s);
    } catch (e) {
      if (mounted) snack(context, e.toString(), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(context.tr('new_booking')),
      content: SizedBox(
        width: 520,
        child: loading
            ? const SizedBox(
                height: 80, child: Center(child: CircularProgressIndicator()))
            : loadError != null
                ? Text(loadError!)
                : SingleChildScrollView(
                    child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Banner2(context.tr('simulated_banner'),
                              icon: Icons.science_outlined),
                          const SizedBox(height: 12),
                          DropdownButtonFormField<int>(
                            initialValue: leadId,
                            isExpanded: true,
                            decoration: InputDecoration(
                                labelText: context.tr('select_lead')),
                            items: [
                              for (final l in leads)
                                DropdownMenuItem(
                                    value: l.id,
                                    child: Text(l.optedOut
                                        ? '${l.name} (${context.tr('opted_out')})'
                                        : l.name))
                            ],
                            onChanged: (v) {
                              setState(() => leadId = v);
                              _loadSlots();
                            },
                          ),
                          const SizedBox(height: 12),
                          DropdownButtonFormField<int>(
                            initialValue: propertyId,
                            isExpanded: true,
                            decoration: InputDecoration(
                                labelText: context.tr('select_property')),
                            items: [
                              for (final p in props)
                                DropdownMenuItem(
                                    value: p.id,
                                    child: Text('${p.title} · ${p.code}',
                                        overflow: TextOverflow.ellipsis))
                            ],
                            onChanged: (v) {
                              setState(() => propertyId = v);
                              _loadSlots();
                            },
                          ),
                          const SizedBox(height: 12),
                          OutlinedButton.icon(
                            icon: const Icon(Icons.calendar_today),
                            label: Text(_dayStr),
                            onPressed: () async {
                              final d = await showDatePicker(
                                  context: context,
                                  initialDate: day,
                                  firstDate: DateTime.now(),
                                  lastDate: DateTime.now()
                                      .add(const Duration(days: 180)));
                              if (d != null) {
                                setState(() => day = d);
                                _loadSlots();
                              }
                            },
                          ),
                          const SizedBox(height: 12),
                          Text(context.tr('available_slots'),
                              style: Theme.of(context).textTheme.titleSmall),
                          const SizedBox(height: 8),
                          if (propertyId == null)
                            Text(context.tr('select_property'))
                          else
                            Wrap(spacing: 8, runSpacing: 8, children: [
                              for (final s in slots)
                                Tooltip(
                                  message: s.reason == null
                                      ? ''
                                      : context.tr(s.reason!),
                                  child: ChoiceChip(
                                    label: Text(
                                        '${s.start.hour.toString().padLeft(2, '0')}:00'),
                                    selected: chosen == s.start,
                                    onSelected: s.available
                                        ? (_) =>
                                            setState(() => chosen = s.start)
                                        : null,
                                  ),
                                ),
                            ]),
                        ]),
                  ),
      ),
      actions: [
        TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(context.tr('cancel'))),
        FilledButton(
          onPressed: (leadId == null || propertyId == null || chosen == null)
              ? null
              : () async {
                  final ok = await runAction(
                      context,
                      () => ref
                          .read(repoProvider)
                          .createBooking(leadId!, propertyId!, chosen!),
                      ok: context.tr('saved'));
                  if (ok && context.mounted) {
                    Navigator.pop(context, true);
                  } else {
                    _loadSlots(); // refresh slots after a conflict
                  }
                },
          child: Text(context.tr('create')),
        ),
      ],
    );
  }
}
