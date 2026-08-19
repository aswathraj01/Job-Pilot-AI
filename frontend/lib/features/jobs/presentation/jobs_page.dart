import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:timeago/timeago.dart' as timeago;

import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/common_widgets.dart';
import '../data/jobs_repository.dart';

class JobsPage extends ConsumerStatefulWidget {
  const JobsPage({super.key});

  @override
  ConsumerState<JobsPage> createState() => _JobsPageState();
}

class _JobsPageState extends ConsumerState<JobsPage> {
  final _searchCtrl = TextEditingController();

  final _statuses = [
    null, 'saved', 'processing', 'applied', 'phone_screen', 'interview', 'offer', 'rejected'
  ];

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final jobsAsync = ref.watch(jobsListProvider);
    final filter = ref.watch(jobsFilterProvider);

    return Scaffold(
      backgroundColor: AppTheme.background,
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeader(context),
          _buildFilterBar(filter),
          const Divider(height: 1),
          Expanded(
            child: jobsAsync.when(
              loading: () => _buildSkeletons(),
              error: (e, _) => Center(child: Text('Error: $e', style: const TextStyle(color: AppTheme.error))),
              data: (result) => result.items.isEmpty
                  ? _buildEmptyState(context)
                  : _buildJobsList(result),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(32, 32, 32, 16),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('My Applications', style: Theme.of(context).textTheme.headlineLarge),
                const SizedBox(height: 4),
                Consumer(builder: (_, ref, __) {
                  final total = ref.watch(jobsListProvider).value?.total ?? 0;
                  return Text('$total jobs tracked', style: Theme.of(context).textTheme.bodyMedium);
                }),
              ],
            ),
          ),
          ElevatedButton.icon(
            onPressed: () => context.go('/jobs/add'),
            icon: const Icon(Icons.add, size: 18),
            label: const Text('Track New Job'),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterBar(JobsFilter filter) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(32, 0, 32, 16),
      child: Row(
        children: [
          // Search
          Expanded(
            child: SizedBox(
              height: 44,
              child: TextField(
                controller: _searchCtrl,
                decoration: InputDecoration(
                  hintText: 'Search jobs, companies...',
                  prefixIcon: const Icon(Icons.search, size: 18),
                  contentPadding: const EdgeInsets.symmetric(vertical: 0, horizontal: 16),
                  suffixIcon: _searchCtrl.text.isNotEmpty
                      ? IconButton(
                          icon: const Icon(Icons.clear, size: 18),
                          onPressed: () {
                            _searchCtrl.clear();
                            ref.read(jobsFilterProvider.notifier).update((s) => s.copyWith(search: ''));
                          },
                        )
                      : null,
                ),
                onChanged: (v) => ref.read(jobsFilterProvider.notifier).update((s) => s.copyWith(search: v)),
              ),
            ),
          ),
          const SizedBox(width: 16),
          // Status filter
          SizedBox(
            height: 44,
            child: DropdownButtonFormField<String?>(
              value: filter.status,
              decoration: const InputDecoration(
                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 0),
                constraints: BoxConstraints(minWidth: 160),
              ),
              hint: const Text('All Statuses'),
              items: _statuses.map((s) => DropdownMenuItem(
                value: s,
                child: Text(s == null ? 'All Statuses' : AppTheme.statusLabel(s)),
              )).toList(),
              onChanged: (s) => ref.read(jobsFilterProvider.notifier).update(
                (f) => s == null ? f.copyWith(clearStatus: true) : f.copyWith(status: s),
              ),
              dropdownColor: AppTheme.surface,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildJobsList(JobsListResult result) {
    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(32, 16, 32, 32),
      itemCount: result.items.length,
      separatorBuilder: (_, __) => const SizedBox(height: 12),
      itemBuilder: (context, i) => _JobCard(job: result.items[i])
          .animate(delay: Duration(milliseconds: i * 40))
          .fadeIn(duration: 300.ms)
          .slideY(begin: 0.05),
    );
  }

  Widget _buildSkeletons() {
    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(32, 16, 32, 32),
      itemCount: 6,
      separatorBuilder: (_, __) => const SizedBox(height: 12),
      itemBuilder: (_, __) => const JobCardSkeleton(),
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 80,
            height: 80,
            decoration: BoxDecoration(
              color: AppTheme.surfaceVariant.withOpacity(0.5),
              borderRadius: BorderRadius.circular(20),
            ),
            child: const Icon(Icons.work_off_outlined, size: 40, color: AppTheme.textMuted),
          ),
          const SizedBox(height: 24),
          Text('No jobs tracked yet', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 8),
          Text('Paste a job URL to start tracking', style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 28),
          ElevatedButton.icon(
            onPressed: () => context.go('/jobs/add'),
            icon: const Icon(Icons.add),
            label: const Text('Track Your First Job'),
          ),
        ],
      ).animate().fadeIn(duration: 400.ms).scale(begin: const Offset(0.95, 0.95)),
    );
  }
}

class _JobCard extends ConsumerWidget {
  final JobSummary job;
  const _JobCard({required this.job});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return InkWell(
      onTap: () => context.go('/jobs/${job.id}'),
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: AppTheme.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppTheme.surfaceVariant.withOpacity(0.5)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                _CompanyAvatar(company: job.company ?? 'J'),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        job.title ?? 'Processing...',
                        style: Theme.of(context).textTheme.titleMedium,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 2),
                      Text(
                        job.company ?? 'Extracting...',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                StatusBadge(status: job.status),
              ],
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: [
                if (job.location != null) _InfoChip(icon: Icons.location_on_outlined, label: job.location!),
                if (job.remoteType != null) _InfoChip(icon: Icons.home_work_outlined, label: AppTheme.statusLabel(job.remoteType!)),
                if (job.salaryMin != null || job.salaryMax != null) _InfoChip(icon: Icons.attach_money, label: job.salaryRange),
                _InfoChip(icon: Icons.schedule_outlined, label: timeago.format(job.createdAt)),
              ],
            ),
            if (job.skillsRequired != null && job.skillsRequired!.isNotEmpty) ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 6,
                runSpacing: 4,
                children: job.skillsRequired!.take(5).map((s) => Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: AppTheme.primary.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: AppTheme.primary.withOpacity(0.2)),
                  ),
                  child: Text(s, style: const TextStyle(color: AppTheme.primaryLight, fontSize: 11, fontWeight: FontWeight.w500)),
                )).toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _CompanyAvatar extends StatelessWidget {
  final String company;
  const _CompanyAvatar({required this.company});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 48,
      height: 48,
      decoration: BoxDecoration(
        gradient: AppGradients.primaryGradient,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Center(
        child: Text(
          company.isNotEmpty ? company[0].toUpperCase() : 'J',
          style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w700),
        ),
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  final IconData icon;
  final String label;
  const _InfoChip({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 13, color: AppTheme.textMuted),
        const SizedBox(width: 4),
        Text(label, style: const TextStyle(color: AppTheme.textMuted, fontSize: 12)),
      ],
    );
  }
}
