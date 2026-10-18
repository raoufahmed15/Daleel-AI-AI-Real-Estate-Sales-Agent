import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import 'api_client.dart';
import 'l10n.dart';
import 'theme.dart';

String fmtMoney(BuildContext c, num? v) =>
    v == null ? c.tr('not_provided') : '${NumberFormat.decimalPattern().format(v)} ${c.tr('egp')}';
String fmtDate(DateTime d) => DateFormat('yyyy-MM-dd HH:mm').format(d);
String orNotProvided(BuildContext c, Object? v) => (v == null || v.toString().isEmpty) ? c.tr('not_provided') : v.toString();

void snack(BuildContext c, String msg, {bool error = false}) {
  ScaffoldMessenger.of(c).showSnackBar(SnackBar(
    content: Text(msg),
    backgroundColor: error ? Theme.of(c).colorScheme.error : null,
  ));
}

/// Runs an API action, shows success/error feedback, returns true on success.
Future<bool> runAction(BuildContext c, Future<dynamic> Function() action, {String? ok}) async {
  try {
    await action();
    if (ok != null && c.mounted) snack(c, ok);
    return true;
  } on ApiException catch (e) {
    if (c.mounted) snack(c, e.message, error: true);
  } catch (e) {
    if (c.mounted) snack(c, e.toString(), error: true);
  }
  return false;
}

Future<bool> confirm(BuildContext c, String message) async {
  final r = await showDialog<bool>(
    context: c,
    builder: (_) => AlertDialog(
      content: Text(message),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(c.tr('no'))),
        FilledButton(onPressed: () => Navigator.pop(c, true), child: Text(c.tr('yes'))),
      ],
    ),
  );
  return r ?? false;
}

class AsyncBody<T> extends StatelessWidget {
  const AsyncBody({required this.value, required this.builder, this.onRetry});
  final AsyncValue<T> value;
  final Widget Function(T data) builder;
  final VoidCallback? onRetry;
  @override
  Widget build(BuildContext context) => value.when(
        data: builder,
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(message: e.toString(), onRetry: onRetry),
      );
}

class ErrorView extends StatelessWidget {
  const ErrorView({required this.message, this.onRetry});
  final String message;
  final VoidCallback? onRetry;
  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Icon(Icons.cloud_off, size: 48, color: Theme.of(context).colorScheme.error),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
            if (onRetry != null) ...[
              const SizedBox(height: 12),
              FilledButton.icon(onPressed: onRetry, icon: const Icon(Icons.refresh), label: Text(context.tr('retry'))),
            ],
          ]),
        ),
      );
}

class StatusChip extends StatelessWidget {
  const StatusChip(this.value, {this.label});
  final String value;
  final String? label;
  @override
  Widget build(BuildContext context) {
    final c = statusColor(value);
    return Chip(
      label: Text(label ?? context.tr(value), style: TextStyle(color: c, fontSize: 12, fontWeight: FontWeight.w600)),
      side: BorderSide(color: c.withValues(alpha: .5)),
      backgroundColor: c.withValues(alpha: .08),
      visualDensity: VisualDensity.compact,
      padding: EdgeInsets.zero,
    );
  }
}

class SectionCard extends StatelessWidget {
  const SectionCard({required this.title, required this.child, this.trailing});
  final String title;
  final Widget child;
  final Widget? trailing;
  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text(title, style: Theme.of(context).textTheme.titleMedium)),
              if (trailing != null) trailing!,
            ]),
            const SizedBox(height: 12),
            child,
          ]),
        ),
      );
}

class MetricCard extends StatelessWidget {
  const MetricCard({required this.label, required this.value, required this.icon});
  final String label, value;
  final IconData icon;
  @override
  Widget build(BuildContext context) => SizedBox(
        width: 190,
        child: Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Icon(icon, color: Theme.of(context).colorScheme.primary),
              const SizedBox(height: 8),
              Text(value, style: Theme.of(context).textTheme.headlineMedium),
              Text(label, style: Theme.of(context).textTheme.bodySmall),
            ]),
          ),
        ),
      );
}

class InfoRow extends StatelessWidget {
  const InfoRow(this.label, this.value);
  final String label;
  final String value;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(width: 150, child: Text(label, style: Theme.of(context).textTheme.bodySmall)),
          Expanded(child: Text(value)),
        ]),
      );
}

class Banner2 extends StatelessWidget {
  const Banner2(this.text, {this.icon = Icons.info_outline, this.color});
  final String text;
  final IconData icon;
  final Color? color;
  @override
  Widget build(BuildContext context) {
    final c = color ?? Colors.amber.shade800;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: c.withValues(alpha: .1), border: Border.all(color: c.withValues(alpha: .5)), borderRadius: BorderRadius.circular(8)),
      child: Row(children: [Icon(icon, color: c), const SizedBox(width: 8), Expanded(child: Text(text))]),
    );
  }
}

class PageHeader extends StatelessWidget {
  const PageHeader(this.title, {this.actions = const []});
  final String title;
  final List<Widget> actions;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Row(children: [
          Expanded(child: Text(title, style: Theme.of(context).textTheme.headlineSmall)),
          ...actions,
        ]),
      );
}

/// Dropdown whose value may be null ("-").
class NullableDropdown extends StatelessWidget {
  const NullableDropdown({required this.label, required this.value, required this.options, required this.onChanged, this.allowNull = true});
  final String label;
  final String? value;
  final List<String> options;
  final ValueChanged<String?> onChanged;
  final bool allowNull;
  @override
  Widget build(BuildContext context) => DropdownButtonFormField<String?>(
        initialValue: value,
        decoration: InputDecoration(labelText: label),
        isExpanded: true,
        items: [
          if (allowNull) const DropdownMenuItem<String?>(value: null, child: Text('-')),
          ...options.map((o) => DropdownMenuItem<String?>(value: o, child: Text(context.tr(o)))),
        ],
        onChanged: onChanged,
      );
}

String? Function(String?) intValidator(BuildContext c) => (v) {
      if (v == null || v.trim().isEmpty) return null;
      final n = int.tryParse(v.trim());
      return (n == null || n < 0) ? c.tr('invalid_number') : null;
    };

int? parseInt(String s) => s.trim().isEmpty ? null : int.tryParse(s.trim());
String? nullIfEmpty(String s) => s.trim().isEmpty ? null : s.trim();

const kPropertyTypes = ['apartment', 'villa', 'townhouse', 'duplex', 'studio', 'penthouse', 'chalet', 'office'];
const kTimelines = ['immediate', '1_3_months', '3_6_months', '6_12_months', 'over_12_months'];
const kLeadStatuses = ['new', 'contacted', 'qualified', 'viewing_scheduled', 'negotiation', 'won', 'lost'];
const kPriorities = ['low', 'medium', 'high'];
const kAvailability = ['available', 'reserved', 'sold'];
const kHandoffCategories = ['hot_lead', 'complaint', 'conflicting_commercial_info', 'discount_request', 'legal_dispute', 'data_deletion_request', 'other'];
const kHandoffStatuses = ['open', 'in_review', 'resolved', 'dismissed'];
