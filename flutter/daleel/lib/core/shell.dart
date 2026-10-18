import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../features/bookings/bookings_screen.dart';
import '../features/conversations/conversation_screen.dart';
import '../features/dashboard/dashboard_screen.dart';
import '../features/handoffs/handoffs_screen.dart';
import '../features/integrations/integrations_screen.dart';
import '../features/leads/crm_screen.dart';
import '../features/leads/leads_screen.dart';
import '../features/properties/properties_screen.dart';
import '../features/settings/settings_screen.dart';
import 'l10n.dart';
import 'providers.dart';

class _Dest {
  const _Dest(this.key, this.icon, this.builder);
  final String key;
  final IconData icon;
  final Widget Function() builder;
}

final _dests = <_Dest>[
  _Dest(
      'nav_dashboard', Icons.dashboard_outlined, () => const DashboardScreen()),
  _Dest('nav_leads', Icons.people_outline, () => const LeadsScreen()),
  _Dest('nav_properties', Icons.apartment, () => const PropertiesScreen()),
  _Dest('nav_conversation', Icons.chat_outlined, () => const ConversationScreen()),
  _Dest('nav_crm', Icons.account_tree_outlined, () => const CrmScreen()),
  _Dest('nav_bookings', Icons.event_available_outlined,
      () => const BookingsScreen()),
  _Dest('nav_handoffs', Icons.support_agent, () => const HandoffsScreen()),
  _Dest('nav_integrations', Icons.extension_outlined,
      () => const IntegrationsScreen()),
  _Dest('nav_settings', Icons.settings_outlined, () => const SettingsScreen()),
];

class AppShell extends ConsumerWidget {
  const AppShell({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final index = ref.watch(navIndexProvider);
    final size = MediaQuery.of(context).size;
    final wide = size.width >= 800 && size.height >= 600;
    final body = Padding(
        padding: const EdgeInsets.all(16), child: _dests[index].builder());
    final banner = Material(
      color: Colors.amber.shade100,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        child: Text(context.tr('demo_banner'),
            style: const TextStyle(fontSize: 12, color: Colors.black87),
            textAlign: TextAlign.center),
      ),
    );
    void select(int i) => ref.read(navIndexProvider.notifier).state = i;

    if (wide) {
      return Scaffold(
        body: SafeArea(
          child: Column(children: [
            banner,
            Expanded(
              child: Row(children: [
                NavigationRail(
                  extended: MediaQuery.of(context).size.width >= 1100,
                  selectedIndex: index,
                  onDestinationSelected: select,
                  labelType: MediaQuery.of(context).size.width >= 1100
                      ? NavigationRailLabelType.none
                      : NavigationRailLabelType.all,
                  leading: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    child: Text('Daleel AI',
                        style: Theme.of(context).textTheme.titleMedium),
                  ),
                  destinations: [
                    for (final d in _dests)
                      NavigationRailDestination(
                          icon: Icon(d.icon), label: Text(context.tr(d.key)))
                  ],
                ),
                const VerticalDivider(width: 1),
                Expanded(child: body),
              ]),
            ),
          ]),
        ),
      );
    }
    return Scaffold(
      appBar: AppBar(title: Text(context.tr(_dests[index].key))),
      drawer: Drawer(
        child: SafeArea(
          child: ListView(children: [
            Padding(
                padding: const EdgeInsets.all(16),
                child: Text('Daleel AI',
                    style: Theme.of(context).textTheme.titleLarge)),
            for (var i = 0; i < _dests.length; i++)
              ListTile(
                leading: Icon(_dests[i].icon),
                title: Text(context.tr(_dests[i].key)),
                selected: i == index,
                onTap: () {
                  select(i);
                  Navigator.pop(context);
                },
              ),
          ]),
        ),
      ),
      body: SafeArea(child: Column(children: [banner, Expanded(child: body)])),
    );
  }
}
