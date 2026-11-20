import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/l10n.dart';
import '../../core/models.dart';
import '../../core/providers.dart';
import '../../core/widgets.dart';
import '../properties/properties_screen.dart';
import '../properties/property_detail_screen.dart';

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  final _searchController = TextEditingController();
  String? _selectedType;

  @override
  void initState() {
    super.initState();
    final filters = ref.read(propertyFiltersProvider);
    _searchController.text = filters['q'] as String? ?? '';
    _selectedType = filters['property_type'] as String?;
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _searchProperties() {
    final filters = {...ref.read(propertyFiltersProvider)};
    final query = _searchController.text.trim();
    if (query.isEmpty) {
      filters.remove('q');
    } else {
      filters['q'] = query;
    }
    ref.read(propertyFiltersProvider.notifier).state = filters;
  }

  void _selectType(String? type) {
    setState(() => _selectedType = type);
    final filters = {...ref.read(propertyFiltersProvider)};
    if (type == null) {
      filters.remove('property_type');
    } else {
      filters['property_type'] = type;
    }
    ref.read(propertyFiltersProvider.notifier).state = filters;
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: () async {
        await Future.wait([
          ref.refresh(propertiesProvider.future),
          ref.refresh(dashboardProvider.future),
        ]);
      },
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          _WelcomeCard(
            searchController: _searchController,
            onSearch: _searchProperties,
          ),
          const SizedBox(height: 24),
          Text(context.tr('quick_categories'),
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 12),
          SizedBox(
            height: 42,
            child: ListView(
              scrollDirection: Axis.horizontal,
              children: [
                _CategoryChip(
                  label: context.tr('all_properties'),
                  icon: Icons.grid_view_rounded,
                  selected: _selectedType == null,
                  onTap: () => _selectType(null),
                ),
                for (final entry in const [
                  ('apartment', Icons.apartment_rounded),
                  ('villa', Icons.villa_outlined),
                  ('chalet', Icons.beach_access_outlined),
                ])
                  _CategoryChip(
                    label: context.tr(entry.$1),
                    icon: entry.$2,
                    selected: _selectedType == entry.$1,
                    onTap: () => _selectType(entry.$1),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          _FeaturedProperties(
            selectedType: _selectedType,
            onSeeAll: () => ref.read(navIndexProvider.notifier).state = 3,
          ),
          const SizedBox(height: 28),
          _DashboardMetrics(
            value: ref.watch(dashboardProvider),
            onRetry: () => ref.invalidate(dashboardProvider),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

class _WelcomeCard extends StatelessWidget {
  const _WelcomeCard({
    required this.searchController,
    required this.onSearch,
  });

  final TextEditingController searchController;
  final VoidCallback onSearch;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: colors.primary.withValues(alpha: .42)),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF282018), Color(0xFF15110D), Color(0xFF100E0C)],
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Icon(Icons.auto_awesome, size: 16, color: colors.primary),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                context.tr('brand_tagline'),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: colors.secondary,
                      letterSpacing: 1.1,
                    ),
              ),
            ),
          ]),
          const SizedBox(height: 14),
          Text(
            context.tr('discover_title'),
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  height: 1.12,
                  fontWeight: FontWeight.w500,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            context.tr('discover_subtitle'),
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: colors.onSurfaceVariant,
                  height: 1.5,
                ),
          ),
          const SizedBox(height: 20),
          TextField(
            controller: searchController,
            textInputAction: TextInputAction.search,
            onSubmitted: (_) => onSearch(),
            decoration: InputDecoration(
              hintText: context.tr('search_properties_hint'),
              prefixIcon: const Icon(Icons.search_rounded),
              suffixIcon: IconButton(
                tooltip: context.tr('search'),
                onPressed: onSearch,
                icon: const Icon(Icons.arrow_forward_rounded),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _CategoryChip extends StatelessWidget {
  const _CategoryChip({
    required this.label,
    required this.icon,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsetsDirectional.only(end: 8),
        child: FilterChip(
          avatar: Icon(icon, size: 18),
          label: Text(label),
          selected: selected,
          onSelected: (_) => onTap(),
          showCheckmark: false,
        ),
      );
}

class _FeaturedProperties extends ConsumerWidget {
  const _FeaturedProperties({
    required this.selectedType,
    required this.onSeeAll,
  });

  final String? selectedType;
  final VoidCallback onSeeAll;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final properties = ref.watch(propertiesProvider);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(children: [
          Expanded(
            child: Text(
              context.tr('featured_properties'),
              style: Theme.of(context).textTheme.titleLarge,
            ),
          ),
          TextButton(
            onPressed: onSeeAll,
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Text(context.tr('see_all')),
              const SizedBox(width: 4),
              const Icon(Icons.arrow_forward_rounded, size: 16),
            ]),
          ),
        ]),
        const SizedBox(height: 12),
        AsyncBody<PageResult<Property>>(
          value: properties,
          onRetry: () => ref.invalidate(propertiesProvider),
          builder: (page) {
            final items = page.items
                .where((property) =>
                    selectedType == null ||
                    property.propertyType == selectedType)
                .take(6)
                .toList();
            if (items.isEmpty) {
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 20),
                child: Text(context.tr('no_results')),
              );
            }
            return SizedBox(
              height: 254,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: items.length,
                separatorBuilder: (_, __) => const SizedBox(width: 12),
                itemBuilder: (context, index) => _PropertyCard(
                  property: items[index],
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) =>
                          PropertyDetailScreen(propertyId: items[index].id),
                    ),
                  ),
                ),
              ),
            );
          },
        ),
      ],
    );
  }
}

class _PropertyCard extends StatelessWidget {
  const _PropertyCard({required this.property, required this.onTap});

  final Property property;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return SizedBox(
      width: 272,
      child: Card(
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                height: 142,
                width: double.infinity,
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      Color(0xFF5A4530),
                      Color(0xFF30271F),
                      Color(0xFF1C1916),
                    ],
                  ),
                ),
                child: Stack(children: [
                  Positioned(
                    right: -14,
                    bottom: -34,
                    child: Icon(
                      Icons.apartment_rounded,
                      size: 174,
                      color: colors.primary.withValues(alpha: .25),
                    ),
                  ),
                  Positioned(
                    left: 12,
                    top: 12,
                    child: StatusChip(property.availability),
                  ),
                  const Center(
                    child: Icon(
                      Icons.home_work_outlined,
                      size: 42,
                      color: Color(0xFFE1C49F),
                    ),
                  ),
                ]),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(14, 12, 14, 10),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      property.title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.titleSmall,
                    ),
                    const SizedBox(height: 5),
                    Row(children: [
                      Icon(Icons.location_on_outlined,
                          size: 15, color: colors.secondary),
                      const SizedBox(width: 3),
                      Expanded(
                        child: Text(
                          property.location,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style:
                              Theme.of(context).textTheme.bodySmall?.copyWith(
                                    color: colors.onSurfaceVariant,
                                  ),
                        ),
                      ),
                    ]),
                    const SizedBox(height: 7),
                    Text(
                      fmtMoney(context, property.price),
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            color: colors.primary,
                            fontWeight: FontWeight.w600,
                          ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DashboardMetrics extends StatelessWidget {
  const _DashboardMetrics({required this.value, required this.onRetry});

  final AsyncValue<Map<String, dynamic>> value;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => AsyncBody<Map<String, dynamic>>(
        value: value,
        onRetry: onRetry,
        builder: (data) {
          final calculated = data['calculated'] as Map<String, dynamic>;
          final byStatus =
              calculated['leads_by_status'] as Map<String, dynamic>;
          final total = calculated['leads_total'] as int;
          final unavailableAi = (data['unavailable_ai_metrics'] as List)
              .cast<Map<String, dynamic>>();
          return Column(
            children: [
              SectionCard(
                title: context.tr('calculated_metrics'),
                child: Column(
                  children: [
                    Wrap(spacing: 12, runSpacing: 12, children: [
                      MetricCard(
                          label: context.tr('total_leads'),
                          value: '${calculated['leads_total']}',
                          icon: Icons.people_outline),
                      MetricCard(
                          label: context.tr('available_properties'),
                          value: '${calculated['properties_available']}',
                          icon: Icons.apartment),
                      MetricCard(
                          label: context.tr('upcoming_viewings'),
                          value: '${calculated['bookings_upcoming']}',
                          icon: Icons.event),
                      MetricCard(
                          label: context.tr('pending_handoffs'),
                          value: '${calculated['handoffs_pending']}',
                          icon: Icons.support_agent),
                      MetricCard(
                          label: context.tr('bookings_scheduled'),
                          value: '${calculated['bookings_scheduled_total']}',
                          icon: Icons.event_available),
                      MetricCard(
                          label: context.tr('bookings_cancelled'),
                          value: '${calculated['bookings_cancelled']}',
                          icon: Icons.event_busy),
                      MetricCard(
                          label: context.tr('crm_activities'),
                          value: '${calculated['crm_activities_total']}',
                          icon: Icons.history),
                      MetricCard(
                          label: context.tr('fully_qualified'),
                          value: '${calculated['leads_fully_qualified']}',
                          icon: Icons.fact_check),
                      MetricCard(
                          label: context.tr('opted_out'),
                          value: '${calculated['leads_opted_out']}',
                          icon: Icons.block),
                    ]),
                    const SizedBox(height: 20),
                    Align(
                      alignment: AlignmentDirectional.centerStart,
                      child: Text(
                        context.tr('leads_by_status'),
                        style: Theme.of(context).textTheme.titleSmall,
                      ),
                    ),
                    const SizedBox(height: 10),
                    for (final entry in byStatus.entries)
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 5),
                        child: Row(children: [
                          SizedBox(
                            width: 110,
                            child: Text(
                              context.tr(entry.key),
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ),
                          Expanded(
                            child: LinearProgressIndicator(
                              value:
                                  total == 0 ? 0 : (entry.value as int) / total,
                              minHeight: 7,
                              borderRadius: BorderRadius.circular(8),
                            ),
                          ),
                          SizedBox(
                            width: 36,
                            child: Text('${entry.value}',
                                textAlign: TextAlign.end),
                          ),
                        ]),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              SectionCard(
                title: context.tr('ai_metrics_unavailable'),
                child: Column(children: [
                  for (final metric in unavailableAi)
                    ListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.lock_outline),
                      title: Text(metric['name'] as String),
                      trailing: StatusChip(
                        metric['status'] as String,
                        label: context.tr('not_integrated'),
                      ),
                    ),
                  Text(context.tr('ai_metrics_note'),
                      style: Theme.of(context).textTheme.bodySmall),
                ]),
              ),
            ],
          );
        },
      );
}
