import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/l10n.dart';
import '../../core/models.dart';
import '../../core/providers.dart';
import '../../core/widgets.dart';
import 'property_form_screen.dart';

final propertyProvider = FutureProvider.autoDispose.family<Property, int>((ref, id) => ref.watch(repoProvider).property(id));

class PropertyDetailScreen extends ConsumerWidget {
  const PropertyDetailScreen({required this.propertyId});
  final int propertyId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final value = ref.watch(propertyProvider(propertyId));
    return Scaffold(
      appBar: AppBar(
        title: Text(value.valueOrNull?.title ?? context.tr('nav_properties')),
        actions: [
          if (value.hasValue) ...[
            IconButton(
              icon: const Icon(Icons.edit),
              onPressed: () async {
                await Navigator.push(context, MaterialPageRoute(builder: (_) => PropertyFormScreen(property: value.value)));
                ref.invalidate(propertyProvider(propertyId));
              },
            ),
            IconButton(
              icon: const Icon(Icons.delete_outline),
              onPressed: () async {
                if (!await confirm(context, context.tr('confirm_delete'))) return;
                if (!context.mounted) return;
                if (await runAction(context, () => ref.read(repoProvider).deleteProperty(propertyId), ok: context.tr('deleted')) && context.mounted) {
                  Navigator.pop(context);
                }
              },
            ),
          ],
        ],
      ),
      body: AsyncBody<Property>(
        value: value,
        onRetry: () => ref.invalidate(propertyProvider(propertyId)),
        builder: (p) => ListView(padding: const EdgeInsets.all(16), children: [
          SectionCard(
            title: p.code,
            trailing: StatusChip(p.availability),
            child: Column(children: [
              InfoRow(context.tr('property_type'), context.tr(p.propertyType)),
              InfoRow(context.tr('location'), p.location),
              InfoRow(context.tr('price'), fmtMoney(context, p.price)),
              InfoRow(context.tr('area'), p.areaSqm == null ? context.tr('not_provided') : '${p.areaSqm} ${context.tr('sqm')}'),
              InfoRow(context.tr('bedrooms'), orNotProvided(context, p.bedrooms)),
              InfoRow(context.tr('delivery_date'), orNotProvided(context, p.deliveryDate)),
              InfoRow(context.tr('payment_plan'), orNotProvided(context, p.paymentPlan)),
              InfoRow(context.tr('description'), orNotProvided(context, p.description)),
            ]),
          ),
          const SizedBox(height: 8),
          Text(context.tr('no_fabrication_note'), style: Theme.of(context).textTheme.bodySmall),
        ]),
      ),
    );
  }
}
