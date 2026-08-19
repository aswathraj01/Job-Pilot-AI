import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/presentation/login_page.dart';
import '../../features/auth/presentation/register_page.dart';
import '../../features/auth/providers/auth_provider.dart';
import '../../features/dashboard/presentation/dashboard_page.dart';
import '../../features/jobs/presentation/add_job_page.dart';
import '../../features/jobs/presentation/job_detail_page.dart';
import '../../features/jobs/presentation/jobs_page.dart';
import '../../features/resume/presentation/resume_page.dart';
import '../../features/settings/presentation/settings_page.dart';
import '../shell/app_shell.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authStateProvider);

  return GoRouter(
    initialLocation: '/jobs',
    redirect: (context, state) {
      final isLoggedIn = authState.isAuthenticated;
      final isAuthRoute = state.matchedLocation.startsWith('/login') ||
          state.matchedLocation.startsWith('/register');

      if (!isLoggedIn && !isAuthRoute) return '/login';
      if (isLoggedIn && isAuthRoute) return '/jobs';
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (_, __) => const LoginPage()),
      GoRoute(path: '/register', builder: (_, __) => const RegisterPage()),
      ShellRoute(
        builder: (context, state, child) => AppShell(child: child),
        routes: [
          GoRoute(
            path: '/jobs',
            pageBuilder: (_, __) => _fadeTransition(const JobsPage()),
            routes: [
              GoRoute(
                path: 'add',
                pageBuilder: (_, __) => _slideTransition(const AddJobPage()),
              ),
              GoRoute(
                path: ':id',
                pageBuilder: (ctx, state) => _slideTransition(
                  JobDetailPage(jobId: state.pathParameters['id']!),
                ),
              ),
            ],
          ),
          GoRoute(
            path: '/dashboard',
            pageBuilder: (_, __) => _fadeTransition(const DashboardPage()),
          ),
          GoRoute(
            path: '/resume',
            pageBuilder: (_, __) => _fadeTransition(const ResumePage()),
          ),
          GoRoute(
            path: '/settings',
            pageBuilder: (_, __) => _fadeTransition(const SettingsPage()),
          ),
        ],
      ),
    ],
  );
});

CustomTransitionPage<void> _fadeTransition(Widget child) {
  return CustomTransitionPage(
    child: child,
    transitionsBuilder: (_, animation, __, child) =>
        FadeTransition(opacity: animation, child: child),
    transitionDuration: const Duration(milliseconds: 200),
  );
}

CustomTransitionPage<void> _slideTransition(Widget child) {
  return CustomTransitionPage(
    child: child,
    transitionsBuilder: (_, animation, __, child) => SlideTransition(
      position: Tween<Offset>(
        begin: const Offset(1.0, 0.0),
        end: Offset.zero,
      ).animate(CurvedAnimation(parent: animation, curve: Curves.easeOutCubic)),
      child: child,
    ),
    transitionDuration: const Duration(milliseconds: 300),
  );
}
