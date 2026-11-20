import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:daleel_ai/core/providers.dart';
import 'package:daleel_ai/core/models.dart';
import 'package:daleel_ai/features/conversations/conversation_screen.dart';
import 'package:daleel_ai/features/properties/properties_screen.dart';
import 'package:daleel_ai/main.dart';

void main() {
  testWidgets('dashboard is the home page and RAG chat remains reachable',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1200, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          propertiesProvider.overrideWith(
            (ref) async => PageResult<Property>([
              Property.fromJson({
                'id': 1,
                'code': 'V-001',
                'title': 'Palm Residence',
                'property_type': 'villa',
                'location': 'New Cairo',
                'area_sqm': 300,
                'bedrooms': 4,
                'price': 12500000,
                'availability': 'available',
              }),
            ], 1),
          ),
          dashboardProvider.overrideWith(
            (ref) async => {
              'calculated': {
                'leads_by_status': {'new': 1},
                'leads_total': 1,
                'properties_available': 0,
                'bookings_upcoming': 0,
                'bookings_scheduled_total': 0,
                'bookings_cancelled': 0,
                'crm_activities_total': 0,
                'leads_fully_qualified': 0,
                'leads_opted_out': 0,
              },
              'unavailable_ai_metrics': <Map<String, dynamic>>[],
            },
          ),
        ],
        child: const DaleelApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byType(NavigationRail), findsOneWidget);
    expect(find.text('Daleel AI'), findsOneWidget);
    expect(find.text('Calculated from stored records'), findsOneWidget);
    expect(find.text('Total leads'), findsOneWidget);
    expect(find.text('Palm Residence'), findsOneWidget);
    await tester.tap(find.byIcon(Icons.chat_bubble_outline));
    await tester.pumpAndSettle();
    expect(
      find.textContaining('Welcome! I am Daleel’s real-estate assistant.'),
      findsOneWidget,
    );
    expect(find.byIcon(Icons.mic_none), findsOneWidget);
    expect(
        find.byTooltip('Upload an image and extract its text'), findsOneWidget);
    await tester.tap(find.byIcon(Icons.mic_none));
    await tester.pumpAndSettle();
    expect(find.text('Voice transcription privacy'), findsOneWidget);
    expect(
      find.textContaining('QwenCleo Arabic speech-recognition model'),
      findsOneWidget,
    );
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();
    await tester.tap(find.byIcon(Icons.dashboard_outlined));
    await tester.pumpAndSettle();
    expect(find.text('Calculated from stored records'), findsOneWidget);
    expect(find.text('Total leads'), findsOneWidget);

    tester.view.physicalSize = const Size(1200, 500);
    await tester.pumpAndSettle();
    expect(find.byType(NavigationRail), findsNothing);
    expect(find.byType(NavigationBar), findsNothing);
    expect(tester.takeException(), isNull);
    tester.view.physicalSize = const Size(390, 844);
    await tester.pumpAndSettle();
    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.text('Featured properties'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.tap(find.text('More'));
    await tester.pumpAndSettle();
    expect(find.text('Human Handoff'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.tap(find.text('Human Handoff'));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });

  testWidgets('AI sandbox is reachable with an empty lead database',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1200, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          propertiesProvider.overrideWith(
            (ref) async => PageResult<Property>([], 0),
          ),
          dashboardProvider.overrideWith(
            (ref) async => {
              'calculated': {
                'leads_by_status': <String, int>{},
                'leads_total': 0,
                'properties_available': 0,
                'bookings_upcoming': 0,
                'bookings_scheduled_total': 0,
                'bookings_cancelled': 0,
                'crm_activities_total': 0,
                'leads_fully_qualified': 0,
                'leads_opted_out': 0,
              },
              'unavailable_ai_metrics': <Map<String, dynamic>>[],
            },
          ),
          conversationLeadsProvider.overrideWith(
            (ref) async => PageResult<Lead>([], 0),
          ),
        ],
        child: const DaleelApp(),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byIcon(Icons.chat_outlined));
    await tester.pumpAndSettle();

    expect(find.text('Add a lead first to start a sandbox conversation.'),
        findsOneWidget);
    expect(find.text('New lead'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
