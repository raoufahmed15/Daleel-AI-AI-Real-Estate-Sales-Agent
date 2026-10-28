import 'api_client.dart';
import 'models.dart';

typedef Json = Map<String, dynamic>;

/// All backend calls live here; UI never builds URLs.
class Repository {
  Repository(this.api, this.ragApi);
  final ApiClient api;
  final ApiClient ragApi;

  PageResult<T> _page<T>(dynamic d, T Function(Json) f) =>
      PageResult((d['items'] as List).map((e) => f(e as Json)).toList(), d['total'] as int);

  Future<RagAnswer> askRag(String query, String sessionId) async =>
      RagAnswer.fromJson(await ragApi.post('/api/chat', body: {
        'query': query,
        'session_id': sessionId,
      }) as Json);

  Future<Json> health() async => await api.get('/api/health') as Json;
  Future<Json> dashboard() async => await api.get('/api/dashboard') as Json;
  Future<Json> integrations() async => await api.get('/api/integrations') as Json;
  Future<Json> settings() async => await api.get('/api/settings') as Json;

  // Conversation sandbox. No messages are sent to an external provider.
  Future<Conversation> openConversation(int leadId, String channel) async =>
      Conversation.fromJson(await api.post('/api/conversations', body: {
        'lead_id': leadId,
        'channel': channel,
      }) as Json);
  Future<Conversation> sendMessage(int conversationId, String text) async =>
      Conversation.fromJson(await api.post(
          '/api/conversations/$conversationId/messages',
          body: {'text': text}) as Json);

  // Leads
  Future<PageResult<Lead>> leads({String? q, String? status, int limit = 200}) async =>
      _page(await api.get('/api/leads', query: {'q': q, 'status': status, 'limit': limit}), Lead.fromJson);
  Future<Lead> lead(int id) async => Lead.fromJson(await api.get('/api/leads/$id') as Json);
  Future<Lead> createLead(Json body) async => Lead.fromJson(await api.post('/api/leads', body: body) as Json);
  Future<Lead> updateLead(int id, Json body) async => Lead.fromJson(await api.patch('/api/leads/$id', body: body) as Json);
  Future<Lead> updateStage(int id, String status) async =>
      Lead.fromJson(await api.put('/api/leads/$id/stage', body: {'status': status}) as Json);
  Future<Lead> updateConsent(int id, Json body) async =>
      Lead.fromJson(await api.put('/api/leads/$id/consent', body: body) as Json);
  Future<Crm> crm(int id) async => Crm.fromJson(await api.get('/api/leads/$id/crm') as Json);
  Future<void> addNote(int id, String text) => api.post('/api/leads/$id/activities', body: {'type': 'note', 'description': text});
  Future<Json> followUps(int id) async => await api.get('/api/leads/$id/follow-ups') as Json;

  // Properties
  Future<PageResult<Property>> properties(Map<String, dynamic> filters) async =>
      _page(await api.get('/api/properties', query: {...filters, 'limit': 200}), Property.fromJson);
  Future<Property> property(int id) async => Property.fromJson(await api.get('/api/properties/$id') as Json);
  Future<Property> createProperty(Json body) async => Property.fromJson(await api.post('/api/properties', body: body) as Json);
  Future<Property> updateProperty(int id, Json body) async =>
      Property.fromJson(await api.patch('/api/properties/$id', body: body) as Json);
  Future<void> deleteProperty(int id) => api.delete('/api/properties/$id');

  // Bookings
  Future<List<Slot>> slots(int propertyId, String day, int? leadId) async =>
      ((await api.get('/api/bookings/slots', query: {'property_id': propertyId, 'day': day, 'lead_id': leadId})) as List)
          .map((e) => Slot.fromJson(e as Json))
          .toList();
  Future<List<Booking>> bookings({String? status, bool upcoming = false}) async =>
      ((await api.get('/api/bookings', query: {'status': status, 'upcoming': upcoming ? 'true' : null})) as List)
          .map((e) => Booking.fromJson(e as Json))
          .toList();
  Future<Booking> createBooking(int leadId, int propertyId, DateTime start) async => Booking.fromJson(await api.post(
      '/api/bookings',
      body: {'lead_id': leadId, 'property_id': propertyId, 'start': start.toIso8601String()}) as Json);
  Future<void> cancelBooking(int id, {String? reason}) => api.post('/api/bookings/$id/cancel', body: {'reason': reason});

  // Handoffs
  Future<List<Handoff>> handoffs({String? status}) async =>
      ((await api.get('/api/handoffs', query: {'status': status})) as List).map((e) => Handoff.fromJson(e as Json)).toList();
  Future<Handoff> handoff(int id) async => Handoff.fromJson(await api.get('/api/handoffs/$id') as Json);
  Future<Handoff> createHandoff(Json body) async => Handoff.fromJson(await api.post('/api/handoffs', body: body) as Json);
  Future<Handoff> updateHandoff(int id, Json body) async =>
      Handoff.fromJson(await api.patch('/api/handoffs/$id', body: body) as Json);
}
