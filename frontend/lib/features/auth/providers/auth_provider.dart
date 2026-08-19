import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

import '../../../core/network/dio_client.dart';
import '../../../core/storage/token_storage.dart';

part 'auth_provider.freezed.dart';

// ── Auth State ────────────────────────────────────────────────────────────────

@freezed
class AuthState with _$AuthState {
  const factory AuthState.initial() = _Initial;
  const factory AuthState.authenticated({required String email, required String name}) = _Authenticated;
  const factory AuthState.unauthenticated() = _Unauthenticated;
  const factory AuthState.loading() = _Loading;
  const factory AuthState.error(String message) = _Error;
}

extension AuthStateX on AuthState {
  bool get isAuthenticated => this is _Authenticated;
}

// ── Auth Notifier ─────────────────────────────────────────────────────────────

class AuthNotifier extends AsyncNotifier<AuthState> {
  @override
  Future<AuthState> build() async {
    final storage = ref.read(tokenStorageProvider);
    final hasToken = await storage.hasToken();
    if (!hasToken) return const AuthState.unauthenticated();

    // Validate token by calling /auth/me
    try {
      final dio = ref.read(dioProvider);
      final resp = await dio.get('/auth/me');
      return AuthState.authenticated(
        email: resp.data['email'] as String,
        name: resp.data['full_name'] as String,
      );
    } catch (_) {
      await storage.clearTokens();
      return const AuthState.unauthenticated();
    }
  }

  Future<void> register(String email, String password, String fullName) async {
    state = const AsyncValue.loading();
    try {
      final dio = ref.read(dioProvider);
      final storage = ref.read(tokenStorageProvider);
      final resp = await dio.post('/auth/register', data: {
        'email': email,
        'password': password,
        'full_name': fullName,
      });
      await storage.saveTokens(
        accessToken: resp.data['access_token'] as String,
        refreshToken: resp.data['refresh_token'] as String,
      );
      // Get user info
      final meResp = await dio.get('/auth/me');
      state = AsyncValue.data(AuthState.authenticated(
        email: meResp.data['email'] as String,
        name: meResp.data['full_name'] as String,
      ));
    } on DioException catch (e) {
      final msg = e.response?.data['detail']?.toString() ?? 'Registration failed';
      state = AsyncValue.data(AuthState.error(msg));
    }
  }

  Future<void> login(String email, String password) async {
    state = const AsyncValue.loading();
    try {
      final dio = ref.read(dioProvider);
      final storage = ref.read(tokenStorageProvider);
      final resp = await dio.post('/auth/login', data: {'email': email, 'password': password});
      await storage.saveTokens(
        accessToken: resp.data['access_token'] as String,
        refreshToken: resp.data['refresh_token'] as String,
      );
      final meResp = await dio.get('/auth/me');
      state = AsyncValue.data(AuthState.authenticated(
        email: meResp.data['email'] as String,
        name: meResp.data['full_name'] as String,
      ));
    } on DioException catch (e) {
      final msg = e.response?.data['detail']?.toString() ?? 'Login failed';
      state = AsyncValue.data(AuthState.error(msg));
    }
  }

  Future<void> logout() async {
    final storage = ref.read(tokenStorageProvider);
    try {
      final refreshToken = await storage.getRefreshToken();
      final dio = ref.read(dioProvider);
      if (refreshToken != null) {
        await dio.post('/auth/logout', data: {'refresh_token': refreshToken});
      }
    } catch (_) {}
    await storage.clearTokens();
    state = const AsyncValue.data(AuthState.unauthenticated());
  }
}

final authStateProvider = AsyncNotifierProvider<AuthNotifier, AuthState>(AuthNotifier.new);
