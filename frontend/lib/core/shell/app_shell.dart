import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../theme/app_theme.dart';

/// Responsive sidebar shell for authenticated pages.
class AppShell extends StatelessWidget {
  final Widget child;
  const AppShell({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    final isNarrow = width < 1024;

    if (isNarrow) {
      return _MobileShell(child: child);
    }
    return _DesktopShell(child: child);
  }
}

class _DesktopShell extends StatelessWidget {
  final Widget child;
  const _DesktopShell({required this.child});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Row(
        children: [
          const _Sidebar(),
          Expanded(
            child: Container(
              color: AppTheme.background,
              child: child,
            ),
          ),
        ],
      ),
    );
  }
}

class _MobileShell extends StatelessWidget {
  final Widget child;
  const _MobileShell({required this.child});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: child,
      bottomNavigationBar: _BottomNav(),
    );
  }
}

class _Sidebar extends StatelessWidget {
  const _Sidebar();

  static const _navItems = [
    _NavItem(icon: Icons.work_outline_rounded, label: 'Jobs', path: '/jobs'),
    _NavItem(icon: Icons.dashboard_outlined, label: 'Dashboard', path: '/dashboard'),
    _NavItem(icon: Icons.description_outlined, label: 'Resume', path: '/resume'),
    _NavItem(icon: Icons.settings_outlined, label: 'Settings', path: '/settings'),
  ];

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;

    return Container(
      width: 240,
      decoration: BoxDecoration(
        color: AppTheme.surface,
        border: Border(right: BorderSide(color: AppTheme.surfaceVariant.withOpacity(0.5))),
      ),
      child: Column(
        children: [
          // Logo
          Padding(
            padding: const EdgeInsets.all(24),
            child: Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    gradient: AppGradients.primaryGradient,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.rocket_launch_rounded, color: Colors.white, size: 20),
                ),
                const SizedBox(width: 12),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Job-Pilot', style: Theme.of(context).textTheme.titleMedium),
                    Text('AI Tracker', style: Theme.of(context).textTheme.bodySmall),
                  ],
                ),
              ],
            ),
          ),

          // Add Job Button
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: () => context.go('/jobs/add'),
                icon: const Icon(Icons.add, size: 18),
                label: const Text('Add Job'),
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Nav items
          ...(_navItems.map((item) => _SidebarNavItem(
                item: item,
                isSelected: location.startsWith(item.path),
              ))),

          const Spacer(),

          // User / Logout at bottom
          const _SidebarFooter(),
          const SizedBox(height: 16),
        ],
      ),
    );
  }
}

class _SidebarNavItem extends StatelessWidget {
  final _NavItem item;
  final bool isSelected;
  const _SidebarNavItem({required this.item, required this.isSelected});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.primary.withOpacity(0.15) : Colors.transparent,
          borderRadius: BorderRadius.circular(10),
        ),
        child: ListTile(
          onTap: () => context.go(item.path),
          leading: Icon(
            item.icon,
            color: isSelected ? AppTheme.primary : AppTheme.textSecondary,
            size: 20,
          ),
          title: Text(
            item.label,
            style: TextStyle(
              color: isSelected ? AppTheme.primary : AppTheme.textSecondary,
              fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
              fontSize: 14,
            ),
          ),
          dense: true,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          selectedColor: AppTheme.primary,
        ),
      ),
    );
  }
}

class _SidebarFooter extends ConsumerWidget {
  const _SidebarFooter();

  @override
  Widget build(BuildContext context, ref) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12),
      child: ListTile(
        onTap: () {
          // ref.read(authStateProvider.notifier).logout();
        },
        leading: const Icon(Icons.logout_outlined, color: AppTheme.textMuted, size: 20),
        title: const Text('Sign out', style: TextStyle(color: AppTheme.textMuted, fontSize: 14)),
        dense: true,
      ),
    );
  }
}

class _BottomNav extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    return NavigationBar(
      backgroundColor: AppTheme.surface,
      selectedIndex: _indexForLocation(location),
      onDestinationSelected: (i) {
        const paths = ['/jobs', '/dashboard', '/resume', '/settings'];
        context.go(paths[i]);
      },
      destinations: const [
        NavigationDestination(icon: Icon(Icons.work_outline_rounded), label: 'Jobs'),
        NavigationDestination(icon: Icon(Icons.dashboard_outlined), label: 'Analytics'),
        NavigationDestination(icon: Icon(Icons.description_outlined), label: 'Resume'),
        NavigationDestination(icon: Icon(Icons.settings_outlined), label: 'Settings'),
      ],
    );
  }

  int _indexForLocation(String loc) {
    if (loc.startsWith('/dashboard')) return 1;
    if (loc.startsWith('/resume')) return 2;
    if (loc.startsWith('/settings')) return 3;
    return 0;
  }
}

class _NavItem {
  final IconData icon;
  final String label;
  final String path;
  const _NavItem({required this.icon, required this.label, required this.path});
}
