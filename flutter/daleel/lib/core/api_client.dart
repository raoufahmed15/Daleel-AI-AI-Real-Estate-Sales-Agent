import 'dart:convert';

import 'package:http/http.dart' as http;

class ApiException implements Exception {
  ApiException(this.status, this.code, this.message);
  final int status;
  final String code;
  final String message;
  @override
  String toString() => message;
}

/// Thin HTTP client. No UI or business logic here.
class ApiClient {
  ApiClient(this.baseUrl);
  final String baseUrl;
  final http.Client _client = http.Client();

  Uri _uri(String path, Map<String, dynamic>? query) {
    final params = <String, String>{};
    query?.forEach((k, v) {
      if (v != null && v.toString().isNotEmpty) params[k] = v.toString();
    });
    return Uri.parse('$baseUrl$path').replace(queryParameters: params.isEmpty ? null : params);
  }

  Future<dynamic> _send(String method, String path, {Map<String, dynamic>? query, Object? body}) async {
    final req = http.Request(method, _uri(path, query));
    req.headers['Content-Type'] = 'application/json';
    if (body != null) req.body = jsonEncode(body);
    http.Response res;
    try {
      final streamed = await _client.send(req).timeout(const Duration(seconds: 15));
      res = await http.Response.fromStream(streamed);
    } catch (_) {
      throw ApiException(0, 'network_error', 'Cannot reach the backend at $baseUrl');
    }
    final text = utf8.decode(res.bodyBytes);
    dynamic data;
    if (text.isNotEmpty) {
      try {
        data = jsonDecode(text);
      } catch (_) {}
    }
    if (res.statusCode >= 200 && res.statusCode < 300) return data;
    var code = 'http_${res.statusCode}';
    var message = 'Request failed (${res.statusCode})';
    if (data is Map && data['error'] is Map) {
      final err = data['error'] as Map;
      code = (err['code'] ?? code).toString();
      message = (err['message'] ?? message).toString();
      final details = err['details'];
      if (details is List && details.isNotEmpty) {
        message += ': ${details.map((d) => d is Map ? '${d['field']} ${d['message']}' : '$d').join('; ')}';
      }
    } else if (data is Map && data['message'] != null) {
      message = data['message'].toString();
    }
    throw ApiException(res.statusCode, code, message);
  }

  Future<dynamic> get(String path, {Map<String, dynamic>? query}) => _send('GET', path, query: query);
  Future<dynamic> post(String path, {Object? body}) => _send('POST', path, body: body);
  Future<dynamic> put(String path, {Object? body}) => _send('PUT', path, body: body);
  Future<dynamic> patch(String path, {Object? body}) => _send('PATCH', path, body: body);
  Future<dynamic> delete(String path) => _send('DELETE', path);
}
