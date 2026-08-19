import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';

import '../../../core/network/dio_client.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/common_widgets.dart';

// ── Data provider ─────────────────────────────────────────────────────────────
final analyticsProvider = FutureProvider.autoDispose<Map<String, dynamic>>((ref) async {
  final dio = ref.watch(dioProvider);
  final resp = await dio.get('/analytics/');
  return resp.data as Map<String, dynamic>;
});

// ── Page ──────────────────────────────────────────────────────────────────────

class DashboardPage extends ConsumerWidget {
  const DashboardPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final analyticsAsync = ref.watch(analyticsProvider);

    return Scaffold(
      backgroundColor: AppTheme.background,
      body: analyticsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e', style: const TextStyle(color: AppTheme.error))),
        data: (data) => _DashboardContent(data: data),
      ),
    );
  }
}

class _DashboardContent extends StatelessWidget {
  final Map<String, dynamic> data;
  const _DashboardContent({required this.data});

  @override
  Widget build(BuildContext context) {
    final summary = data['summary'] as Map<String, dynamic>;
    final timeline = data['timeline'] as Map<String, dynamic>;
    final funnel = data['funnel'] as Map<String, dynamic>;
    final topSkills = (data['top_skills'] as List).cast<Map<String, dynamic>>();
    final topCompanies = (data['top_companies'] as List).cast<Map<String, dynamic>>();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Text('Analytics Dashboard', style: Theme.of(context).textTheme.headlineLarge)
              .animate().fadeIn(duration: 400.ms).slideY(begin: -0.1),
          const SizedBox(height: 4),
          Text('Your job search performance at a glance', style: Theme.of(context).textTheme.bodyMedium)
              .animate(delay: 100.ms).fadeIn(duration: 400.ms),
          const SizedBox(height: 32),

          // KPI Cards
          _KpiGrid(summary: summary)
              .animate(delay: 150.ms).fadeIn(duration: 400.ms).slideY(begin: 0.05),
          const SizedBox(height: 32),

          // Timeline + Funnel row
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                flex: 3,
                child: _TimelineChart(timeline: timeline)
                    .animate(delay: 300.ms).fadeIn(duration: 400.ms),
              ),
              const SizedBox(width: 24),
              Expanded(
                flex: 2,
                child: _FunnelChart(funnel: funnel)
                    .animate(delay: 350.ms).fadeIn(duration: 400.ms),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // Skills + Companies row
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: _TopSkillsCard(skills: topSkills)
                    .animate(delay: 450.ms).fadeIn(duration: 400.ms),
              ),
              const SizedBox(width: 24),
              Expanded(
                child: _TopCompaniesCard(companies: topCompanies)
                    .animate(delay: 500.ms).fadeIn(duration: 400.ms),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _KpiGrid extends StatelessWidget {
  final Map<String, dynamic> summary;
  const _KpiGrid({required this.summary});

  @override
  Widget build(BuildContext context) {
    return GridView.count(
      shrinkWrap: true,
      crossAxisCount: 4,
      crossAxisSpacing: 16,
      mainAxisSpacing: 16,
      childAspectRatio: 1.6,
      physics: const NeverScrollableScrollPhysics(),
      children: [
        MetricCard(
          label: 'Total Tracked',
          value: '${summary['total_jobs'] ?? 0}',
          icon: Icons.work_outline_rounded,
          color: AppTheme.primary,
        ),
        MetricCard(
          label: 'Applied',
          value: '${summary['applied'] ?? 0}',
          icon: Icons.send_outlined,
          color: AppTheme.secondary,
        ),
        MetricCard(
          label: 'Interviews',
          value: '${summary['interview'] ?? 0}',
          icon: Icons.people_outline_rounded,
          color: AppTheme.warning,
        ),
        MetricCard(
          label: 'Response Rate',
          value: '${summary['response_rate_pct'] ?? 0}%',
          icon: Icons.trending_up_rounded,
          color: AppTheme.success,
          subtitle: '(phone screen + interview + offer) / applied',
        ),
      ],
    );
  }
}

class _TimelineChart extends StatelessWidget {
  final Map<String, dynamic> timeline;
  const _TimelineChart({required this.timeline});

  @override
  Widget build(BuildContext context) {
    final points = (timeline['timeline_data'] as List? ?? []).cast<Map<String, dynamic>>();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Applications Over Time', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 24),
            SizedBox(
              height: 220,
              child: points.isEmpty
                  ? const Center(child: Text('No data yet', style: TextStyle(color: AppTheme.textMuted)))
                  : LineChart(
                      LineChartData(
                        gridData: FlGridData(
                          show: true,
                          drawVerticalLine: false,
                          getDrawingHorizontalLine: (_) => const FlLine(color: AppTheme.surfaceVariant, strokeWidth: 1),
                        ),
                        titlesData: FlTitlesData(
                          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                          bottomTitles: AxisTitles(
                            sideTitles: SideTitles(
                              showTitles: true,
                              getTitlesWidget: (v, _) {
                                final i = v.toInt();
                                if (i < 0 || i >= points.length) return const SizedBox.shrink();
                                final period = points[i]['period'] as String;
                                return Text(period.substring(period.length > 7 ? period.length - 5 : 0),
                                    style: const TextStyle(color: AppTheme.textMuted, fontSize: 10));
                              },
                              interval: (points.length / 6).ceilToDouble(),
                            ),
                          ),
                        ),
                        borderData: FlBorderData(show: false),
                        lineBarsData: [
                          LineChartBarData(
                            spots: points.asMap().entries.map((e) =>
                                FlSpot(e.key.toDouble(), (e.value['count'] as int).toDouble())).toList(),
                            isCurved: true,
                            color: AppTheme.primary,
                            barWidth: 3,
                            dotData: const FlDotData(show: false),
                            belowBarData: BarAreaData(
                              show: true,
                              gradient: LinearGradient(
                                colors: [AppTheme.primary.withOpacity(0.3), AppTheme.primary.withOpacity(0.0)],
                                begin: Alignment.topCenter,
                                end: Alignment.bottomCenter,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

class _FunnelChart extends StatelessWidget {
  final Map<String, dynamic> funnel;
  const _FunnelChart({required this.funnel});

  @override
  Widget build(BuildContext context) {
    final stages = (funnel['stages'] as List? ?? []).cast<Map<String, dynamic>>();
    final maxCount = stages.isEmpty ? 1 : stages.map((s) => s['count'] as int).reduce((a, b) => a > b ? a : b);

    final colors = [
      AppTheme.primary, AppTheme.secondary, AppTheme.warning, AppTheme.success, AppTheme.primaryLight
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Application Funnel', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 24),
            ...stages.asMap().entries.map((entry) {
              final i = entry.key;
              final stage = entry.value;
              final count = stage['count'] as int;
              final pct = stage['conversion_pct'] as double?;
              final color = colors[i % colors.length];
              final width = maxCount == 0 ? 0.0 : count / maxCount;

              return Padding(
                padding: const EdgeInsets.only(bottom: 14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(AppTheme.statusLabel(stage['stage'] as String),
                            style: const TextStyle(fontSize: 13, color: AppTheme.textSecondary)),
                        Row(children: [
                          Text('$count', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: color)),
                          if (pct != null) ...[
                            const SizedBox(width: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: color.withOpacity(0.15),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text('$pct%', style: TextStyle(fontSize: 10, color: color, fontWeight: FontWeight.w600)),
                            ),
                          ],
                        ]),
                      ],
                    ),
                    const SizedBox(height: 6),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(4),
                      child: LinearProgressIndicator(
                        value: width,
                        backgroundColor: AppTheme.surfaceVariant,
                        valueColor: AlwaysStoppedAnimation<Color>(color),
                        minHeight: 8,
                      ),
                    ),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }
}

class _TopSkillsCard extends StatelessWidget {
  final List<Map<String, dynamic>> skills;
  const _TopSkillsCard({required this.skills});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Most In-Demand Skills', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 16),
            if (skills.isEmpty)
              const Text('Apply to more jobs to see skill trends', style: TextStyle(color: AppTheme.textMuted))
            else
              ...skills.take(10).map((skill) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Row(
                  children: [
                    Expanded(child: Text(skill['skill'] as String, style: const TextStyle(fontSize: 13))),
                    const SizedBox(width: 8),
                    Text('${skill['count']}', style: const TextStyle(color: AppTheme.textMuted, fontSize: 12)),
                    const SizedBox(width: 8),
                    SizedBox(
                      width: 80,
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: (skill['pct_of_jobs'] as num).toDouble() / 100,
                          backgroundColor: AppTheme.surfaceVariant,
                          valueColor: const AlwaysStoppedAnimation<Color>(AppTheme.secondary),
                          minHeight: 6,
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text('${(skill['pct_of_jobs'] as num).toStringAsFixed(0)}%',
                        style: const TextStyle(color: AppTheme.secondary, fontSize: 11)),
                  ],
                ),
              )),
          ],
        ),
      ),
    );
  }
}

class _TopCompaniesCard extends StatelessWidget {
  final List<Map<String, dynamic>> companies;
  const _TopCompaniesCard({required this.companies});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Top Companies Applied', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 16),
            if (companies.isEmpty)
              const Text('No data yet', style: TextStyle(color: AppTheme.textMuted))
            else
              ...companies.take(8).asMap().entries.map((entry) {
                final i = entry.key;
                final company = entry.value;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Row(
                    children: [
                      Container(
                        width: 32,
                        height: 32,
                        decoration: BoxDecoration(
                          color: AppTheme.primary.withOpacity(0.1 + i * 0.05),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Center(
                          child: Text(
                            (company['company'] as String)[0].toUpperCase(),
                            style: const TextStyle(color: AppTheme.primary, fontWeight: FontWeight.w700, fontSize: 14),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(child: Text(company['company'] as String, style: const TextStyle(fontSize: 13))),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(
                          color: AppTheme.primary.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text('${company['count']} jobs',
                            style: const TextStyle(color: AppTheme.primary, fontSize: 11, fontWeight: FontWeight.w600)),
                      ),
                    ],
                  ),
                );
              }),
          ],
        ),
      ),
    );
  }
}
