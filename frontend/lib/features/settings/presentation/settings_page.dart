import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/network/dio_client.dart';
import '../../../core/theme/app_theme.dart';
import '../../../features/auth/providers/auth_provider.dart';
import '../../../shared/widgets/gradient_button.dart';

class SettingsPage extends ConsumerStatefulWidget {
  const SettingsPage({super.key});

  @override
  ConsumerState<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends ConsumerState<SettingsPage> {
  bool _gmailConnected = false;
  bool _connectingGmail = false;

  Future<void> _connectGmail() async {
    setState(() => _connectingGmail = true);
    try {
      final dio = ref.read(dioProvider);
      final resp = await dio.get('/email/connect');
      final authUrl = resp.data['auth_url'] as String;
      await launchUrl(Uri.parse(authUrl), mode: LaunchMode.externalApplication);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to connect Gmail: $e'), backgroundColor: AppTheme.error),
        );
      }
    } finally {
      setState(() => _connectingGmail = false);
    }
  }

  Future<void> _disconnectGmail() async {
    try {
      await ref.read(dioProvider).delete('/email/disconnect');
      setState(() => _gmailConnected = false);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e'), backgroundColor: AppTheme.error),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authStateProvider).value;
    final userEmail = authState is _Authenticated ? (authState as dynamic).email as String : '';
    final userName = authState is _Authenticated ? (authState as dynamic).name as String : '';

    return Scaffold(
      backgroundColor: AppTheme.background,
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(32),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Settings', style: Theme.of(context).textTheme.headlineLarge)
                  .animate().fadeIn(duration: 400.ms),
              const SizedBox(height: 32),

              // ── Profile ──────────────────────────────────────────────────
              _Section(
                title: 'Profile',
                icon: Icons.person_outline_rounded,
                child: Column(
                  children: [
                    _InfoRow(label: 'Full Name', value: userName),
                    const Divider(height: 1),
                    _InfoRow(label: 'Email', value: userEmail),
                  ],
                ),
              ).animate(delay: 100.ms).fadeIn(duration: 400.ms),
              const SizedBox(height: 20),

              // ── Gmail Integration ────────────────────────────────────────
              _Section(
                title: 'Gmail Integration',
                icon: Icons.email_outlined,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Connect your Gmail to automatically sync recruiter emails and link them to your tracked jobs.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 20),
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                          decoration: BoxDecoration(
                            color: (_gmailConnected ? AppTheme.success : AppTheme.surfaceVariant).withOpacity(0.15),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Row(children: [
                            Icon(
                              _gmailConnected ? Icons.check_circle_rounded : Icons.radio_button_unchecked,
                              size: 14,
                              color: _gmailConnected ? AppTheme.success : AppTheme.textMuted,
                            ),
                            const SizedBox(width: 6),
                            Text(
                              _gmailConnected ? 'Connected' : 'Not connected',
                              style: TextStyle(
                                color: _gmailConnected ? AppTheme.success : AppTheme.textMuted,
                                fontSize: 13, fontWeight: FontWeight.w600,
                              ),
                            ),
                          ]),
                        ),
                        const Spacer(),
                        if (_gmailConnected)
                          OutlinedButton(
                            onPressed: _disconnectGmail,
                            style: OutlinedButton.styleFrom(foregroundColor: AppTheme.error, side: const BorderSide(color: AppTheme.error)),
                            child: const Text('Disconnect'),
                          )
                        else
                          GradientButton(
                            onPressed: _connectingGmail ? null : _connectGmail,
                            isLoading: _connectingGmail,
                            height: 42,
                            child: const Row(children: [
                              Icon(Icons.email_outlined, size: 16),
                              SizedBox(width: 8),
                              Text('Connect Gmail'),
                            ]),
                          ),
                      ],
                    ),
                  ],
                ),
              ).animate(delay: 200.ms).fadeIn(duration: 400.ms),
              const SizedBox(height: 20),

              // ── Chrome Extension ─────────────────────────────────────────
              _Section(
                title: 'Chrome Extension',
                icon: Icons.extension_outlined,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Install the Job-Pilot Chrome extension to save jobs from any job board with a single click.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 16),
                    OutlinedButton.icon(
                      onPressed: () {},
                      icon: const Icon(Icons.download_outlined, size: 16),
                      label: const Text('Download Extension'),
                    ),
                  ],
                ),
              ).animate(delay: 300.ms).fadeIn(duration: 400.ms),
              const SizedBox(height: 20),

              // ── Account Actions ──────────────────────────────────────────
              _Section(
                title: 'Account',
                icon: Icons.manage_accounts_outlined,
                child: Column(
                  children: [
                    ListTile(
                      leading: const Icon(Icons.logout_outlined, color: AppTheme.error),
                      title: const Text('Sign Out', style: TextStyle(color: AppTheme.error)),
                      onTap: () => ref.read(authStateProvider.notifier).logout(),
                      contentPadding: EdgeInsets.zero,
                    ),
                  ],
                ),
              ).animate(delay: 400.ms).fadeIn(duration: 400.ms),
            ],
          ),
        ),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  final String title;
  final IconData icon;
  final Widget child;

  const _Section({required this.title, required this.icon, required this.child});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(icon, size: 18, color: AppTheme.primary),
              const SizedBox(width: 10),
              Text(title, style: Theme.of(context).textTheme.titleMedium),
            ]),
            const SizedBox(height: 20),
            child,
          ],
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  const _InfoRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(
        children: [
          SizedBox(
            width: 120,
            child: Text(label, style: Theme.of(context).textTheme.bodyMedium),
          ),
          Expanded(child: Text(value, style: Theme.of(context).textTheme.bodyLarge)),
        ],
      ),
    );
  }
}
