import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/l10n.dart';
import '../../core/models.dart';
import '../../core/providers.dart';
import '../../core/widgets.dart';
import 'property_detail_screen.dart';
import 'property_form_screen.dart';

final propertyFiltersProvider = StateProvider<Map<String, dynamic>>((ref) => {});

final propertiesProvider = FutureProvider.autoDispose<PageResult<Property>>(
    (ref) => ref.watch(repoProvider).properties(ref.watch(propertyFiltersProvider)));

class PropertiesScreen extends ConsumerStatefulWidget {
  const PropertiesScreen({super.key});
  @override
  ConsumerState<PropertiesScreen> createState() => _PropertiesScreenState();
}

class _PropertiesScreenState extends ConsumerState<PropertiesScreen> {
  final q = TextEditingController();
  final location = TextEditingController();
  final minPrice = TextEditingController();
  final maxPrice = TextEditingController();
  final minBeds = TextEditingController();
  String? type;
  String? availability;
  String sort = 'id';

  @override
  void dispose() {
    for (final c in [q, location, minPrice, maxPrice, minBeds]) {
      c.dispose();
    }
    super.dispose();
  }

  void _apply() {
    ref.read(propertyFiltersProvider.notifier).state = {
      'q': q.text.trim(),
      'location': location.text.trim(),
      'min_price': parseInt(minPrice.text),
      'max_price': parseInt(maxPrice.text),
      'min_bedrooms': parseInt(minBeds.text),
      'property_type': type,
      'availability': availability,
      'sort': sort,
    };
  }

  void _clear() {
    for (final c in [q, location, minPrice, maxPrice, minBeds]) {
      c.clear();
    }
    setState(() {
      type = null;
      availability = null;
      sort = 'id';
    });
    ref.read(propertyFiltersProvider.notifier).state = {};
  }

  @override
  Widget build(BuildContext context) {
    final props = ref.watch(propertiesProvider);
    Widget box(Widget w, [double width = 190]) => SizedBox(width: width, child: w);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      PageHeader(context.tr('nav_properties'), actions: [
        FilledButton.icon(
          icon: const Icon(Icons.add),
          label: Text(context.tr('new_property')),
          onPressed: () async {
            await Navigator.push(context, MaterialPageRoute(builder: (_) => const PropertyFormScreen()));
            ref.invalidate(propertiesProvider);
          },
        ),
      ]),
      ExpansionTile(
        tilePadding: EdgeInsets.zero,
        initiallyExpanded: true,
        title: Text(context.tr('filters')),
        children: [
          Wrap(spacing: 12, runSpacing: 12, children: [
            box(TextField(controller: q, decoration: InputDecoration(labelText: context.tr('search'), prefixIcon: const Icon(Icons.search)), onSubmitted: (_) => _apply()), 240),
            box(TextField(controller: location, decoration: InputDecoration(labelText: context.tr('location')), onSubmitted: (_) => _apply())),
            box(NullableDropdown(label: context.tr('property_type'), value: type, options: kPropertyTypes, onChanged: (v) => setState(() => type = v))),
            box(NullableDropdown(label: context.tr('availability'), value: availability, options: kAvailability, onChanged: (v) => setState(() => availability = v))),
            box(TextField(controller: minPrice, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: context.tr('min_price')))),
            box(TextField(controller: maxPrice, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: context.tr('max_price')))),
            box(TextField(controller: minBeds, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: context.tr('min_bedrooms')))),
            box(NullableDropdown(label: context.tr('sort'), value: sort, options: const ['id', 'price_asc', 'price_desc', 'area_desc'], allowNull: false, onChanged: (v) => setState(() => sort = v!))),
            FilledButton(onPressed: _apply, child: Text(context.tr('apply'))),
            TextButton(onPressed: _clear, child: Text(context.tr('clear'))),
          ]),
          const SizedBox(height: 8),
        ],
      ),
      Expanded(
        child: AsyncBody<PageResult<Property>>(
          value: props,
          onRetry: () => ref.invalidate(propertiesProvider),
          builder: (page) {
            if (page.items.isEmpty) return Center(child: Text(context.tr('no_results')));
            return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${page.total} ${context.tr('results')}', style: Theme.of(context).textTheme.bodySmall),
              Expanded(
                child: ListView.separated(
                  itemCount: page.items.length,
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemBuilder: (_, i) {
                    final p = page.items[i];
                    return ListTile(
                      leading: const CircleAvatar(child: Icon(Icons.home_work_outlined)),
                      title: Text('${p.title} · ${p.code}'),
                      subtitle: Text([
                        fmtMoney(context, p.price),
                        p.areaSqm == null ? context.tr('not_provided') : '${p.areaSqm!.toStringAsFixed(0)} ${context.tr('sqm')}',
                        p.bedrooms == null ? context.tr('not_provided') : '${p.bedrooms} ${context.tr('bedrooms')}',
                      ].join(' · ')),
                      trailing: StatusChip(p.availability),
                      onTap: () async {
                        await Navigator.push(context, MaterialPageRoute(builder: (_) => PropertyDetailScreen(propertyId: p.id)));
                        ref.invalidate(propertiesProvider);
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
