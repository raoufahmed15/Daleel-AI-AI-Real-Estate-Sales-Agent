import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/l10n.dart';
import '../../core/models.dart';
import '../../core/providers.dart';
import '../../core/widgets.dart';

class PropertyFormScreen extends ConsumerStatefulWidget {
  const PropertyFormScreen({this.property});
  final Property? property;
  @override
  ConsumerState<PropertyFormScreen> createState() => _PropertyFormScreenState();
}

class _PropertyFormScreenState extends ConsumerState<PropertyFormScreen> {
  final _key = GlobalKey<FormState>();
  late final Property? p = widget.property;
  late final title = TextEditingController(text: p?.title);
  late final location = TextEditingController(text: p?.location);
  late final area = TextEditingController(text: p?.areaSqm?.toString());
  late final beds = TextEditingController(text: p?.bedrooms?.toString());
  late final price = TextEditingController(text: p?.price?.toString());
  late final delivery = TextEditingController(text: p?.deliveryDate);
  late final plan = TextEditingController(text: p?.paymentPlan);
  late final description = TextEditingController(text: p?.description);
  late String type = p?.propertyType ?? 'apartment';
  late String availability = p?.availability ?? 'available';
  bool saving = false;

  @override
  void dispose() {
    for (final c in [title, location, area, beds, price, delivery, plan, description]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _pickDate() async {
    final now = DateTime.now();
    final d = await showDatePicker(
      context: context,
      initialDate: DateTime.tryParse(delivery.text) ?? now,
      firstDate: DateTime(now.year - 5),
      lastDate: DateTime(now.year + 15),
    );
    if (d != null) delivery.text = d.toIso8601String().substring(0, 10);
  }

  Future<void> _save() async {
    if (!_key.currentState!.validate()) return;
    setState(() => saving = true);
    final body = <String, dynamic>{
      'title': title.text.trim(),
      'property_type': type,
      'location': location.text.trim(),
      'area_sqm': area.text.trim().isEmpty ? null : double.tryParse(area.text.trim()),
      'bedrooms': parseInt(beds.text),
      'price': parseInt(price.text),
      'availability': availability,
      'delivery_date': nullIfEmpty(delivery.text),
      'payment_plan': nullIfEmpty(plan.text),
      'description': nullIfEmpty(description.text),
    };
    final repo = ref.read(repoProvider);
    final ok = await runAction(context, () => p == null ? repo.createProperty(body) : repo.updateProperty(p!.id, body), ok: context.tr('saved'));
    if (!mounted) return;
    setState(() => saving = false);
    if (ok) Navigator.pop(context, true);
  }

  @override
  Widget build(BuildContext context) {
    final intV = intValidator(context);
    String? req(String? v) => (v == null || v.trim().isEmpty) ? context.tr('required') : null;
    Widget gap() => const SizedBox(height: 12);
    return Scaffold(
      appBar: AppBar(title: Text(p == null ? context.tr('new_property') : context.tr('edit_property'))),
      body: Form(
        key: _key,
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 700),
            child: ListView(padding: const EdgeInsets.all(16), children: [
              TextFormField(controller: title, decoration: InputDecoration(labelText: '${context.tr('title')} *'), validator: req),
              gap(),
              Row(children: [
                Expanded(child: NullableDropdown(label: context.tr('property_type'), value: type, options: kPropertyTypes, allowNull: false, onChanged: (v) => setState(() => type = v!))),
                const SizedBox(width: 12),
                Expanded(child: NullableDropdown(label: context.tr('availability'), value: availability, options: kAvailability, allowNull: false, onChanged: (v) => setState(() => availability = v!))),
              ]),
              gap(),
              TextFormField(controller: location, decoration: InputDecoration(labelText: '${context.tr('location')} *'), validator: req),
              gap(),
              Row(children: [
                Expanded(
                  child: TextFormField(
                    controller: area,
                    keyboardType: TextInputType.number,
                    decoration: InputDecoration(labelText: '${context.tr('area')} (${context.tr('sqm')})'),
                    validator: (v) => (v != null && v.trim().isNotEmpty && (double.tryParse(v.trim()) ?? 0) <= 0) ? context.tr('invalid_number') : null,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(child: TextFormField(controller: beds, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: context.tr('bedrooms')), validator: intV)),
              ]),
              gap(),
              TextFormField(controller: price, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: '${context.tr('price')} (${context.tr('egp')})'), validator: intV),
              gap(),
              TextFormField(
                controller: delivery,
                readOnly: true,
                onTap: _pickDate,
                decoration: InputDecoration(
                  labelText: context.tr('delivery_date'),
                  suffixIcon: IconButton(icon: const Icon(Icons.clear), onPressed: () => delivery.clear()),
                ),
              ),
              gap(),
              TextFormField(controller: plan, maxLines: 2, decoration: InputDecoration(labelText: context.tr('payment_plan'))),
              gap(),
              TextFormField(controller: description, maxLines: 3, decoration: InputDecoration(labelText: context.tr('description'))),
              const SizedBox(height: 8),
              Text(context.tr('no_fabrication_note'), style: Theme.of(context).textTheme.bodySmall),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: saving ? null : _save,
                icon: saving ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.save),
                label: Text(context.tr('save')),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}
