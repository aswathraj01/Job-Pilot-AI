import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

const _accessTokenKey = 'access_token';
const _refreshTokenKey = 'refresh_token';

/// Secure local token storage using flutter_secure_storage.
class TokenStorage {
  final FlutterSecureStorage _storage;

  const TokenStorage(this._storage);

  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await Future.wait([
      _storage.write(key: _accessTokenKey, value: accessToken),
      _storage.write(key: _refreshTokenKey, value: refreshToken),
    ]);
  }

  Future<String?> getAccessToken() => _storage.read(key: _accessTokenKey);
  Future<String?> getRefreshToken() => _storage.read(key: _refreshTokenKey);

  Future<void> clearTokens() async {
    await Future.wait([
      _storage.delete(key: _accessTokenKey),
      _storage.delete(key: _refreshTokenKey),
    ]);
  }

  Future<bool> hasToken() async {
    final token = await getAccessToken();
    return token != null && token.isNotEmpty;
  }
}

final tokenStorageProvider = Provider<TokenStorage>((ref) {
  return const TokenStorage(FlutterSecureStorage(
    webOptions: WebOptions(dbName: 'jobpilot', publicKey: 'jobpilot_key'),
  ));
});
