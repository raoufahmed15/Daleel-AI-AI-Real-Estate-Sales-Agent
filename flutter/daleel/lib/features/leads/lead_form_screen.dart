import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/l10n.dart';
import '../../core/models.dart';
import '../../core/providers.dart';
import '../../core/widgets.dart';

class LeadFormScreen extends ConsumerStatefulWidget {
  const LeadFormScreen({this.lead});
  final Lead? lead;
  @override
  ConsumerState<LeadFormScreen> createState() => _LeadFormScreenState();
}

class _LeadFormScreenState extends ConsumerState<LeadFormScreen> {
  final _key = GlobalKey<FormState>();
  late final Lead? l = widget.lead;
  late final name = TextEditingController(text: l?.name);
  late final phone = TextEditingController(text: l?.phone);
  late final email = TextEditingController(text: l?.email);
  late final budget = TextEditingController(text: l?.budget?.toString());
  late final location = TextEditingController(text: l?.preferredLocation);
  late final down = TextEditingController(text: l?.downPayment?.toString());
  late final installment = TextEditingController(text: l?.monthlyInstallment?.toString());
  late final summary = TextEditingController(text: l?.conversationSummary);
  late final nextSteps = TextEditingController(text: l?.nextSteps);
  late String status = l?.status ?? 'new';
  late String priority = l?.priority ?? 'medium';
  String? propertyType;
  String? timeline;
  bool saving = false;

  @override
  void initState() {
    super.initState();
    propertyType = l?.propertyType;
    timeline = l?.purchaseTimeline;
  }

  @override
  void dispose() {
    for (final c in [name, phone, email, budget, location, down, installment, summary, nextSteps]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    if (!_key.currentState!.validate()) return;
    setState(() => saving = true);
    final body = <String, dynamic>{
      'name': name.text.trim(),
      'phone': nullIfEmpty(phone.text),
      'email': nullIfEmpty(email.text),
      'status': status,
      'priority': priority,
      'budget': parseInt(budget.text),
      'preferred_location': nullIfEmpty(location.text),
      'property_type': propertyType,
      'down_payment': parseInt(down.text),
      'monthly_installment': parseInt(installment.text),
      'purchase_timeline': timeline,
      'conversation_summary': nullIfEmpty(summary.text),
      'next_steps': nullIfEmpty(nextSteps.text),
    };
    final repo = ref.read(repoProvider);
    final ok = await runAction(context, () => l == null ? repo.createLead(body) : repo.updateLead(l!.id, body),
        ok: context.tr('saved'));
    if (!mounted) return;
    setState(() => saving = false);
    if (ok) Navigator.pop(context, true);
  }

  @override
  Widget build(BuildContext context) {
    final intV = intValidator(context);
    Widget gap() => const SizedBox(height: 12);
    return Scaffold(
      appBar: AppBar(title: Text(l == null ? context.tr('new_lead') : context.tr('edit_lead'))),
      body: Form(
        key: _key,
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 700),
            child: ListView(padding: const EdgeInsets.all(16), children: [
              TextFormField(
                controller: name,
                decoration: InputDecoration(labelText: '${context.tr('name')} *'),
                validator: (v) => (v == null || v.trim().isEmpty) ? context.tr('required') : null,
              ),
              gap(),
              TextFormField(controller: phone, decoration: InputDecoration(labelText: context.tr('phone')), keyboardType: TextInputType.phone),
              gap(),
              TextFormField(
                controller: email,
                decoration: InputDecoration(labelText: context.tr('email')),
                keyboardType: TextInputType.emailAddress,
                validator: (v) => (v != null && v.trim().isNotEmpty && !v.contains('@')) ? context.tr('invalid_email') : null,
              ),
              gap(),
              Row(children: [
                Expanded(child: NullableDropdown(label: context.tr('status'), value: status, options: kLeadStatuses, allowNull: false, onChanged: (v) => setState(() => status = v!))),
                const SizedBox(width: 12),
                Expanded(child: NullableDropdown(label: context.tr('priority'), value: priority, options: kPriorities, allowNull: false, onChanged: (v) => setState(() => priority = v!))),
              ]),
              const Divider(height: 32),
              Text(context.tr('qualification'), style: Theme.of(context).textTheme.titleMedium),
              Text(context.tr('qualification_hint'), style: Theme.of(context).textTheme.bodySmall),
              gap(),
              TextFormField(controller: budget, decoration: InputDecoration(labelText: '${context.tr('budget')} (${context.tr('egp')})'), keyboardType: TextInputType.number, validator: intV),
              gap(),
              TextFormField(controller: location, decoration: InputDecoration(labelText: context.tr('preferred_location'))),
              gap(),
              NullableDropdown(label: context.tr('property_type'), value: propertyType, options: kPropertyTypes, onChanged: (v) => setState(() => propertyType = v)),
              gap(),
              Row(children: [
                Expanded(child: TextFormField(controller: down, decoration: InputDecoration(labelText: '${context.tr('down_payment')} (${context.tr('egp')})'), keyboardType: TextInputType.number, validator: intV)),
                const SizedBox(width: 12),
                Expanded(child: TextFormField(controller: installment, decoration: InputDecoration(labelText: '${context.tr('monthly_installment')} (${context.tr('egp')})'), keyboardType: TextInputType.number, validator: intV)),
              ]),
              gap(),
              NullableDropdown(label: context.tr('purchase_timeline'), value: timeline, options: kTimelines, onChanged: (v) => setState(() => timeline = v)),
              const Divider(height: 32),
              TextFormField(controller: summary, maxLines: 3, decoration: InputDecoration(labelText: context.tr('conversation_summary'))),
              gap(),
              TextFormField(controller: nextSteps, maxLines: 2, decoration: InputDecoration(labelText: context.tr('next_steps'))),
              const SizedBox(height: 20),
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
