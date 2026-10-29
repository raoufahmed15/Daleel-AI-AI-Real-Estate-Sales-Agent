import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:daleel_ai/core/providers.dart';
import 'package:daleel_ai/core/models.dart';
import 'package:daleel_ai/features/conversations/conversation_screen.dart';
import 'package:daleel_ai/main.dart';

void main() {
  testWidgets('RAG chat is the home page and dashboard remains reachable',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1200, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
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
    expect(
      find.textContaining('Welcome! I am Daleel’s real-estate assistant.'),
      findsOneWidget,
    );
    expect(find.byIcon(Icons.mic_none), findsOneWidget);
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
