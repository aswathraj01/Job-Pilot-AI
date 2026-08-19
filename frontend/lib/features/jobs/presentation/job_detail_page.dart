import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:percent_indicator/percent_indicator.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/common_widgets.dart';
import '../../../shared/widgets/glass_card.dart';
import '../data/jobs_repository.dart';

class JobDetailPage extends ConsumerWidget {
  final String jobId;
  const JobDetailPage({super.key, required this.jobId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailAsync = ref.watch(jobDetailProvider(jobId));

    return Scaffold(
      backgroundColor: AppTheme.background,
      body: detailAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (data) => _JobDetailView(data: data, jobId: jobId),
      ),
    );
  }
}

class _JobDetailView extends ConsumerStatefulWidget {
  final Map<String, dynamic> data;
  final String jobId;
  const _JobDetailView({required this.data, required this.jobId});

  @override
  ConsumerState<_JobDetailView> createState() => _JobDetailViewState();
}

class _JobDetailViewState extends ConsumerState<_JobDetailView> {
  final _noteCtrl = TextEditingController();
  bool _addingNote = false;

  @override
  void dispose() {
    _noteCtrl.dispose();
    super.dispose();
  }

  Future<void> _updateStatus(String newStatus) async {
    await ref.read(jobsRepositoryProvider).updateJobStatus(widget.jobId, newStatus);
    ref.invalidate(jobDetailProvider(widget.jobId));
    ref.invalidate(jobsListProvider);
  }

  Future<void> _addNote() async {
    if (_noteCtrl.text.trim().isEmpty) return;
    await ref.read(jobsRepositoryProvider).addNote(widget.jobId, _noteCtrl.text.trim());
    _noteCtrl.clear();
    setState(() => _addingNote = false);
    ref.invalidate(jobDetailProvider(widget.jobId));
  }

  @override
  Widget build(BuildContext context) {
    final details = widget.data['details'] as Map<String, dynamic>?;
    final notes = (widget.data['notes'] as List? ?? []).cast<Map<String, dynamic>>();
    final reminders = (widget.data['reminders'] as List? ?? []).cast<Map<String, dynamic>>();
    final match = widget.data['resume_match'] as Map<String, dynamic>?;
    final status = widget.data['status'] as String? ?? 'saved';

    return CustomScrollView(
      slivers: [
        // ── App Bar ──────────────────────────────────────────────────
        SliverAppBar(
          backgroundColor: AppTheme.surface,
          expandedHeight: 200,
          pinned: true,
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () => context.go('/jobs'),
          ),
          flexibleSpace: FlexibleSpaceBar(
            background: Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [AppTheme.primary.withOpacity(0.3), AppTheme.surface],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
              ),
              padding: const EdgeInsets.fromLTRB(80, 60, 24, 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  Text(
                    details?['title'] ?? 'Processing...',
                    style: Theme.of(context).textTheme.headlineLarge,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    details?['company'] ?? '',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppTheme.primaryLight),
                  ),
                ],
              ),
            ),
          ),
          actions: [
            // Status update button
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: _StatusDropdown(currentStatus: status, onChanged: _updateStatus),
            ),
            IconButton(
              icon: const Icon(Icons.open_in_new),
              tooltip: 'Open job posting',
              onPressed: () {
                final url = widget.data['url'] as String?;
                if (url != null) launchUrl(Uri.parse(url));
              },
            ),
          ],
        ),

        SliverPadding(
          padding: const EdgeInsets.all(32),
          sliver: SliverList(
            delegate: SliverChildListDelegate([
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Left column — main info
                  Expanded(
                    flex: 3,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (details != null) ...[
                          _JobInfoGrid(details: details),
                          const SizedBox(height: 24),
                          _SkillsSection(skills: (details['skills_required'] as List?)?.cast<String>()),
                          const SizedBox(height: 24),
                          _DescriptionSection(summary: details['description_summary'] as String?),
                          if ((details['responsibilities'] as List?)?.isNotEmpty == true) ...[
                            const SizedBox(height: 24),
                            _BulletListSection(
                              title: 'Responsibilities',
                              items: (details['responsibilities'] as List).cast<String>(),
                              icon: Icons.task_alt_outlined,
                            ),
                          ],
                          if ((details['requirements'] as List?)?.isNotEmpty == true) ...[
                            const SizedBox(height: 24),
                            _BulletListSection(
                              title: 'Requirements',
                              items: (details['requirements'] as List).cast<String>(),
                              icon: Icons.checklist_outlined,
                            ),
                          ],
                          if ((details['benefits'] as List?)?.isNotEmpty == true) ...[
                            const SizedBox(height: 24),
                            _BulletListSection(
                              title: 'Benefits',
                              items: (details['benefits'] as List).cast<String>(),
                              icon: Icons.star_outline_rounded,
                              accentColor: AppTheme.success,
                            ),
                          ],
                        ],
                        const SizedBox(height: 24),
                        _NotesSection(
                          notes: notes,
                          noteCtrl: _noteCtrl,
                          addingNote: _addingNote,
                          onToggleAdd: () => setState(() => _addingNote = !_addingNote),
                          onSubmit: _addNote,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 24),
                  // Right column — match score + reminders
                  Expanded(
                    flex: 1,
                    child: Column(
                      children: [
                        if (match != null) _ResumeMatchCard(match: match),
                        if (reminders.isNotEmpty) ...[
                          const SizedBox(height: 16),
                          _RemindersCard(reminders: reminders),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
            ]),
          ),
        ),
      ],
    );
  }
}

class _StatusDropdown extends StatelessWidget {
  final String currentStatus;
  final ValueChanged<String> onChanged;
  const _StatusDropdown({required this.currentStatus, required this.onChanged});

  static const _statuses = ['saved', 'applied', 'phone_screen', 'interview', 'offer', 'rejected', 'withdrawn'];

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: AppTheme.statusColor(currentStatus).withOpacity(0.15),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.statusColor(currentStatus).withOpacity(0.4)),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: currentStatus,
          isDense: true,
          dropdownColor: AppTheme.surface,
          style: TextStyle(color: AppTheme.statusColor(currentStatus), fontWeight: FontWeight.w600, fontSize: 13),
          icon: Icon(Icons.keyboard_arrow_down, color: AppTheme.statusColor(currentStatus), size: 16),
          items: _statuses.map((s) => DropdownMenuItem(
            value: s,
            child: Text(AppTheme.statusLabel(s)),
          )).toList(),
          onChanged: (s) { if (s != null) onChanged(s); },
        ),
      ),
    );
  }
}

class _JobInfoGrid extends StatelessWidget {
  final Map<String, dynamic> details;
  const _JobInfoGrid({required this.details});

  @override
  Widget build(BuildContext context) {
    final items = [
      if (details['location'] != null) (Icons.location_on_outlined, 'Location', details['location']!),
      if (details['remote_type'] != null) (Icons.home_work_outlined, 'Work Type', AppTheme.statusLabel(details['remote_type']!)),
      if (details['job_type'] != null) (Icons.work_outline_rounded, 'Job Type', AppTheme.statusLabel(details['job_type']!)),
      if (details['salary_min'] != null || details['salary_max'] != null)
        (Icons.attach_money, 'Salary', _salary(details)),
      if (details['experience_years_min'] != null)
        (Icons.timer_outlined, 'Experience', '${details['experience_years_min']}–${details['experience_years_max'] ?? '+'} years'),
      if (details['source_platform'] != null) (Icons.source_outlined, 'Source', details['source_platform']!),
    ];

    if (items.isEmpty) return const SizedBox.shrink();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: GridView.count(
          shrinkWrap: true,
          crossAxisCount: 2,
          crossAxisSpacing: 16,
          mainAxisSpacing: 16,
          childAspectRatio: 3.5,
          physics: const NeverScrollableScrollPhysics(),
          children: items.map((item) {
            final (icon, label, value) = item;
            return Row(
              children: [
                Icon(icon, size: 16, color: AppTheme.primary),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(label, style: const TextStyle(color: AppTheme.textMuted, fontSize: 11)),
                      Text(value, style: const TextStyle(color: AppTheme.textPrimary, fontSize: 13, fontWeight: FontWeight.w500)),
                    ],
                  ),
                ),
              ],
            );
          }).toList(),
        ),
      ),
    );
  }

  String _salary(Map<String, dynamic> d) {
    final min = d['salary_min'];
    final max = d['salary_max'];
    final curr = d['currency'] ?? 'USD';
    if (min != null && max != null) return '\$$min – \$$max $curr';
    return '\$${min ?? max} $curr';
  }
}

class _SkillsSection extends StatelessWidget {
  final List<String>? skills;
  const _SkillsSection({this.skills});

  @override
  Widget build(BuildContext context) {
    if (skills == null || skills!.isEmpty) return const SizedBox.shrink();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              const Icon(Icons.code_rounded, size: 18, color: AppTheme.secondary),
              const SizedBox(width: 8),
              Text('Required Skills', style: Theme.of(context).textTheme.titleMedium),
            ]),
            const SizedBox(height: 16),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: skills!.map((s) => Chip(
                label: Text(s, style: const TextStyle(fontSize: 12)),
                backgroundColor: AppTheme.primary.withOpacity(0.1),
                side: BorderSide(color: AppTheme.primary.withOpacity(0.3)),
              )).toList(),
            ),
          ],
        ),
      ),
    );
  }
}

class _DescriptionSection extends StatelessWidget {
  final String? summary;
  const _DescriptionSection({this.summary});

  @override
  Widget build(BuildContext context) {
    if (summary == null) return const SizedBox.shrink();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              const Icon(Icons.auto_awesome, size: 18, color: AppTheme.primary),
              const SizedBox(width: 8),
              Text('AI Summary', style: Theme.of(context).textTheme.titleMedium),
            ]),
            const SizedBox(height: 12),
            Text(summary!, style: Theme.of(context).textTheme.bodyLarge?.copyWith(height: 1.6)),
          ],
        ),
      ),
    );
  }
}

class _BulletListSection extends StatelessWidget {
  final String title;
  final List<String> items;
  final IconData icon;
  final Color accentColor;

  const _BulletListSection({
    required this.title,
    required this.items,
    required this.icon,
    this.accentColor = AppTheme.primary,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(icon, size: 18, color: accentColor),
              const SizedBox(width: 8),
              Text(title, style: Theme.of(context).textTheme.titleMedium),
            ]),
            const SizedBox(height: 16),
            ...items.map((item) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 6,
                    height: 6,
                    margin: const EdgeInsets.only(top: 8, right: 10),
                    decoration: BoxDecoration(color: accentColor, borderRadius: BorderRadius.circular(3)),
                  ),
                  Expanded(child: Text(item, style: Theme.of(context).textTheme.bodyMedium?.copyWith(height: 1.5))),
                ],
              ),
            )),
          ],
        ),
      ),
    );
  }
}

class _NotesSection extends StatelessWidget {
  final List<Map<String, dynamic>> notes;
  final TextEditingController noteCtrl;
  final bool addingNote;
  final VoidCallback onToggleAdd;
  final VoidCallback onSubmit;

  const _NotesSection({
    required this.notes,
    required this.noteCtrl,
    required this.addingNote,
    required this.onToggleAdd,
    required this.onSubmit,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(children: [
                  const Icon(Icons.notes_rounded, size: 18, color: AppTheme.warning),
                  const SizedBox(width: 8),
                  Text('Notes', style: Theme.of(context).textTheme.titleMedium),
                ]),
                TextButton.icon(
                  onPressed: onToggleAdd,
                  icon: Icon(addingNote ? Icons.close : Icons.add, size: 16),
                  label: Text(addingNote ? 'Cancel' : 'Add Note'),
                ),
              ],
            ),
            if (addingNote) ...[
              const SizedBox(height: 12),
              TextField(
                controller: noteCtrl,
                maxLines: 4,
                decoration: const InputDecoration(hintText: 'Write your note here...'),
              ),
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerRight,
                child: ElevatedButton(onPressed: onSubmit, child: const Text('Save Note')),
              ),
            ],
            if (notes.isEmpty && !addingNote) ...[
              const SizedBox(height: 16),
              Center(child: Text('No notes yet. Add your thoughts!', style: Theme.of(context).textTheme.bodyMedium)),
            ],
            ...notes.map((note) => Container(
              margin: const EdgeInsets.only(top: 12),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppTheme.surfaceVariant.withOpacity(0.4),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(note['content'] as String, style: Theme.of(context).textTheme.bodyMedium),
                  const SizedBox(height: 6),
                  Text(
                    DateFormat('MMM d, y · h:mm a').format(DateTime.parse(note['created_at'] as String).toLocal()),
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            )),
          ],
        ),
      ),
    );
  }
}

class _ResumeMatchCard extends StatelessWidget {
  final Map<String, dynamic> match;
  const _ResumeMatchCard({required this.match});

  @override
  Widget build(BuildContext context) {
    final score = (match['score'] as num).toDouble();
    final matched = (match['matched_skills'] as List?)?.cast<String>() ?? [];
    final gaps = (match['gap_skills'] as List?)?.cast<String>() ?? [];
    final color = score >= 70 ? AppTheme.success : (score >= 40 ? AppTheme.warning : AppTheme.error);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              const Icon(Icons.analytics_outlined, size: 18, color: AppTheme.secondary),
              const SizedBox(width: 8),
              Text('Resume Match', style: Theme.of(context).textTheme.titleMedium),
            ]),
            const SizedBox(height: 20),
            Center(
              child: CircularPercentIndicator(
                radius: 55,
                lineWidth: 10,
                percent: score / 100,
                center: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text('${score.toInt()}%', style: TextStyle(color: color, fontSize: 22, fontWeight: FontWeight.w700)),
                    const Text('match', style: TextStyle(color: AppTheme.textMuted, fontSize: 12)),
                  ],
                ),
                progressColor: color,
                backgroundColor: color.withOpacity(0.15),
                circularStrokeCap: CircularStrokeCap.round,
                animation: true,
                animationDuration: 800,
              ),
            ),
            if (match['ai_summary'] != null) ...[
              const SizedBox(height: 16),
              Text(match['ai_summary'] as String, style: Theme.of(context).textTheme.bodyMedium?.copyWith(height: 1.5)),
            ],
            if (matched.isNotEmpty) ...[
              const SizedBox(height: 16),
              Text('✅ Matched Skills', style: Theme.of(context).textTheme.labelLarge?.copyWith(color: AppTheme.success)),
              const SizedBox(height: 8),
              Wrap(spacing: 6, runSpacing: 6, children: matched.take(5).map((s) => Chip(
                label: Text(s, style: const TextStyle(fontSize: 11)),
                backgroundColor: AppTheme.success.withOpacity(0.1),
                side: BorderSide(color: AppTheme.success.withOpacity(0.3)),
              )).toList()),
            ],
            if (gaps.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text('❌ Skill Gaps', style: Theme.of(context).textTheme.labelLarge?.copyWith(color: AppTheme.error)),
              const SizedBox(height: 8),
              Wrap(spacing: 6, runSpacing: 6, children: gaps.take(5).map((s) => Chip(
                label: Text(s, style: const TextStyle(fontSize: 11)),
                backgroundColor: AppTheme.error.withOpacity(0.1),
                side: BorderSide(color: AppTheme.error.withOpacity(0.3)),
              )).toList()),
            ],
          ],
        ),
      ),
    ).animate().fadeIn(duration: 400.ms).slideX(begin: 0.1);
  }
}

class _RemindersCard extends StatelessWidget {
  final List<Map<String, dynamic>> reminders;
  const _RemindersCard({required this.reminders});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              const Icon(Icons.notifications_outlined, size: 18, color: AppTheme.warning),
              const SizedBox(width: 8),
              Text('Reminders', style: Theme.of(context).textTheme.titleMedium),
            ]),
            const SizedBox(height: 12),
            ...reminders.map((r) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                children: [
                  Icon(r['is_sent'] == true ? Icons.check_circle : Icons.schedule,
                      size: 14, color: r['is_sent'] == true ? AppTheme.success : AppTheme.warning),
                  const SizedBox(width: 8),
                  Expanded(child: Text(r['message'] as String, style: Theme.of(context).textTheme.bodySmall)),
                ],
              ),
            )),
          ],
        ),
      ),
    );
  }
}
