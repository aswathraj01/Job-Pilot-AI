import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../storage/token_storage.dart';

const _baseUrl = String.fromEnvironment('API_URL', defaultValue: 'http://localhost:8000/api/v1');

/// Configured Dio HTTP client with JWT interceptor.
Dio createDio(TokenStorage tokenStorage) {
  final dio = Dio(BaseOptions(
    baseUrl: _baseUrl,
    connectTimeout: const Duration(seconds: 30),
    receiveTimeout: const Duration(seconds: 60),
    headers: {'Content-Type': 'application/json'},
  ));

  // JWT Auth Interceptor
  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await tokenStorage.getAccessToken();
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onError: (error, handler) async {
        if (error.response?.statusCode == 401) {
          // Try token refresh
          final refreshToken = await tokenStorage.getRefreshToken();
          if (refreshToken != null) {
            try {
              final refreshDio = Dio(BaseOptions(baseUrl: _baseUrl));
              final resp = await refreshDio.post(
                '/auth/refresh',
                data: {'refresh_token': refreshToken},
              );
              final newAccessToken = resp.data['access_token'] as String;
              final newRefreshToken = resp.data['refresh_token'] as String;
              await tokenStorage.saveTokens(
                accessToken: newAccessToken,
                refreshToken: newRefreshToken,
              );
              // Retry original request
              error.requestOptions.headers['Authorization'] = 'Bearer $newAccessToken';
              final retryResp = await dio.fetch(error.requestOptions);
              handler.resolve(retryResp);
              return;
            } catch (_) {
              await tokenStorage.clearTokens();
            }
          }
        }
        handler.next(error);
      },
    ),
  );

  return dio;
}

final dioProvider = Provider<Dio>((ref) {
  final storage = ref.watch(tokenStorageProvider);
  return createDio(storage);
});
