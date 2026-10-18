import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/l10n.dart';
import '../../core/models.dart';
import '../../core/providers.dart';
import '../../core/widgets.dart';
import 'lead_detail_screen.dart';
import 'lead_form_screen.dart';

final leadQueryProvider = StateProvider<String>((ref) => '');
final leadStatusFilterProvider = StateProvider<String?>((ref) => null);

final leadsProvider = FutureProvider.autoDispose<PageResult<Lead>>((ref) {
  final q = ref.watch(leadQueryProvider);
  final st = ref.watch(leadStatusFilterProvider);
  return ref.watch(repoProvider).leads(q: q, status: st);
});

class LeadsScreen extends ConsumerStatefulWidget {
  const LeadsScreen({super.key});
  @override
  ConsumerState<LeadsScreen> createState() => _LeadsScreenState();
}

class _LeadsScreenState extends ConsumerState<LeadsScreen> {
  late final TextEditingController _search = TextEditingController(text: ref.read(leadQueryProvider));

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final leads = ref.watch(leadsProvider);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      PageHeader(context.tr('nav_leads'), actions: [
        FilledButton.icon(
          icon: const Icon(Icons.add),
          label: Text(context.tr('new_lead')),
          onPressed: () async {
            await Navigator.push(context, MaterialPageRoute(builder: (_) => const LeadFormScreen()));
            ref.invalidate(leadsProvider);
          },
        ),
      ]),
      Wrap(spacing: 12, runSpacing: 12, crossAxisAlignment: WrapCrossAlignment.center, children: [
        SizedBox(
          width: 300,
          child: TextField(
            controller: _search,
            decoration: InputDecoration(
              hintText: context.tr('search_leads'),
              prefixIcon: const Icon(Icons.search),
              suffixIcon: IconButton(
                icon: const Icon(Icons.clear),
                onPressed: () {
                  _search.clear();
                  ref.read(leadQueryProvider.notifier).state = '';
                },
              ),
            ),
            onSubmitted: (v) => ref.read(leadQueryProvider.notifier).state = v.trim(),
          ),
        ),
        SizedBox(
          width: 220,
          child: NullableDropdown(
            label: context.tr('status'),
            value: ref.watch(leadStatusFilterProvider),
            options: kLeadStatuses,
            onChanged: (v) => ref.read(leadStatusFilterProvider.notifier).state = v,
          ),
        ),
      ]),
      const SizedBox(height: 12),
      Expanded(
        child: AsyncBody<PageResult<Lead>>(
          value: leads,
          onRetry: () => ref.invalidate(leadsProvider),
          builder: (page) {
            if (page.items.isEmpty) return Center(child: Text(context.tr('no_results')));
            return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${page.total} ${context.tr('results')}', style: Theme.of(context).textTheme.bodySmall),
              Expanded(
                child: ListView.separated(
                  itemCount: page.items.length,
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemBuilder: (_, i) {
                    final l = page.items[i];
                    return ListTile(
                      leading: CircleAvatar(child: Text(l.name.isEmpty ? '?' : String.fromCharCode(l.name.runes.first).toUpperCase())),
                      title: Text(l.name),
                      subtitle: Text([
                        orNotProvided(context, l.phone),
                        if (l.preferredLocation != null) l.preferredLocation!,
                      ].join(' · ')),
                      trailing: Wrap(spacing: 6, children: [
                        if (l.optedOut) StatusChip('denied', label: context.tr('opted_out')),
                        StatusChip(l.priority),
                        StatusChip(l.status),
                      ]),
                      onTap: () async {
                        await Navigator.push(context, MaterialPageRoute(builder: (_) => LeadDetailScreen(leadId: l.id)));
                        ref.invalidate(leadsProvider);
                      },
                    );
                  },
                ),
              ),
            ]);
          },
        ),
      ),
    ]);
  }
}
