import 'package:dio/dio.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:percent_indicator/percent_indicator.dart';

import '../../../core/network/dio_client.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/common_widgets.dart';
import '../../../shared/widgets/gradient_button.dart';

// ── Data providers ─────────────────────────────────────────────────────────────

final resumeProvider = FutureProvider.autoDispose<Map<String, dynamic>?>((ref) async {
  final dio = ref.watch(dioProvider);
  try {
    final resp = await dio.get('/resume/');
    return resp.data as Map<String, dynamic>?;
  } on DioException catch (e) {
    if (e.response?.statusCode == 404) return null;
    rethrow;
  }
});

final resumeMatchesProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  final dio = ref.watch(dioProvider);
  final resp = await dio.get('/resume/matches');
  return ((resp.data['items'] as List)).cast<Map<String, dynamic>>();
});

// ── Page ──────────────────────────────────────────────────────────────────────

class ResumePage extends ConsumerStatefulWidget {
  const ResumePage({super.key});

  @override
  ConsumerState<ResumePage> createState() => _ResumePageState();
}

class _ResumePageState extends ConsumerState<ResumePage> {
  bool _uploading = false;

  Future<void> _pickAndUploadResume() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf', 'docx', 'doc'],
      withData: true,
    );
    if (result == null || result.files.isEmpty) return;

    final file = result.files.first;
    setState(() => _uploading = true);

    try {
      final dio = ref.read(dioProvider);
      final formData = FormData.fromMap({
        'file': MultipartFile.fromBytes(
          file.bytes!,
          filename: file.name,
          contentType: DioMediaType.parse(
            file.extension == 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          ),
        ),
      });
      await dio.post('/resume/upload', data: formData);
      ref.invalidate(resumeProvider);
      ref.invalidate(resumeMatchesProvider);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('✅ Resume uploaded and parsed successfully!'), backgroundColor: AppTheme.success),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Upload failed: $e'), backgroundColor: AppTheme.error),
        );
      }
    } finally {
      setState(() => _uploading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final resumeAsync = ref.watch(resumeProvider);
    final matchesAsync = ref.watch(resumeMatchesProvider);

    return Scaffold(
      backgroundColor: AppTheme.background,
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(32),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('Resume & Matching', style: Theme.of(context).textTheme.headlineLarge),
                  Text('Upload your resume for AI-powered job matching', style: Theme.of(context).textTheme.bodyMedium),
                ]),
                GradientButton(
                  onPressed: _uploading ? null : _pickAndUploadResume,
                  isLoading: _uploading,
                  height: 46,
                  child: const Row(children: [
                    Icon(Icons.upload_file_outlined, size: 18),
                    SizedBox(width: 8),
                    Text('Upload Resume'),
                  ]),
                ),
              ],
            ).animate().fadeIn(duration: 400.ms),
            const SizedBox(height: 32),

            // Resume Card
            resumeAsync.when(
              loading: () => const ShimmerBox(width: double.infinity, height: 140, borderRadius: 12),
              error: (e, _) => Text('Error: $e', style: const TextStyle(color: AppTheme.error)),
              data: (resume) => resume == null
                  ? _EmptyResumeCard(onUpload: _pickAndUploadResume)
                  : _ResumeCard(resume: resume),
            ).animate(delay: 200.ms).fadeIn(duration: 400.ms),
            const SizedBox(height: 32),

            // Match Scores
            Text('Job Match Scores', style: Theme.of(context).textTheme.titleLarge)
                .animate(delay: 300.ms).fadeIn(),
            const SizedBox(height: 4),
            Text('AI match scores between your resume and tracked jobs', style: Theme.of(context).textTheme.bodyMedium)
                .animate(delay: 350.ms).fadeIn(),
            const SizedBox(height: 16),
            matchesAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Text('Error: $e'),
              data: (matches) => matches.isEmpty
                  ? _EmptyMatchesCard()
                  : Column(
                      children: matches.asMap().entries.map((entry) =>
                        _MatchScoreRow(match: entry.value)
                            .animate(delay: Duration(milliseconds: 100 + entry.key * 50))
                            .fadeIn(duration: 300.ms)
                            .slideX(begin: 0.05),
                      ).toList(),
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptyResumeCard extends StatelessWidget {
  final VoidCallback onUpload;
  const _EmptyResumeCard({required this.onUpload});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          children: [
            const Icon(Icons.description_outlined, size: 48, color: AppTheme.textMuted),
            const SizedBox(height: 16),
            Text('No resume uploaded yet', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text('Upload a PDF or DOCX resume to enable AI job matching', style: Theme.of(context).textTheme.bodyMedium),
            const SizedBox(height: 20),
            OutlinedButton.icon(
              onPressed: onUpload,
              icon: const Icon(Icons.upload_file_outlined, size: 18),
              label: const Text('Upload PDF or DOCX'),
            ),
          ],
        ),
      ),
    );
  }
}

class _ResumeCard extends StatelessWidget {
  final Map<String, dynamic> resume;
  const _ResumeCard({required this.resume});

  @override
  Widget build(BuildContext context) {
    final skills = (resume['parsed_skills'] as List?)?.cast<String>() ?? [];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 52,
                  height: 52,
                  decoration: BoxDecoration(
                    gradient: AppGradients.primaryGradient,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.description_rounded, color: Colors.white, size: 26),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(resume['filename'] as String, style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 4),
                      Text(
                        '${((resume['file_size_bytes'] as int) / 1024).toStringAsFixed(1)} KB · ${resume['mime_type']}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppTheme.success.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: AppTheme.success.withOpacity(0.3)),
                  ),
                  child: const Row(children: [
                    Icon(Icons.check_circle, size: 12, color: AppTheme.success),
                    SizedBox(width: 4),
                    Text('Active', style: TextStyle(color: AppTheme.success, fontSize: 12, fontWeight: FontWeight.w600)),
                  ]),
                ),
              ],
            ),
            if (skills.isNotEmpty) ...[
              const SizedBox(height: 20),
              Text('Detected Skills (${skills.length})', style: Theme.of(context).textTheme.labelLarge),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 6,
                children: skills.map((s) => Chip(
                  label: Text(s, style: const TextStyle(fontSize: 12)),
                  backgroundColor: AppTheme.primary.withOpacity(0.1),
                )).toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _EmptyMatchesCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Center(
          child: Column(children: [
            const Icon(Icons.analytics_outlined, size: 40, color: AppTheme.textMuted),
            const SizedBox(height: 12),
            Text('No matches yet', style: Theme.of(context).textTheme.bodyMedium),
            const SizedBox(height: 8),
            const Text('Open a job and tap "Match Resume" to get your AI score',
                style: TextStyle(color: AppTheme.textMuted, fontSize: 13), textAlign: TextAlign.center),
          ]),
        ),
      ),
    );
  }
}

class _MatchScoreRow extends StatelessWidget {
  final Map<String, dynamic> match;
  const _MatchScoreRow({required this.match});

  @override
  Widget build(BuildContext context) {
    final score = (match['score'] as num).toDouble();
    final color = score >= 70 ? AppTheme.success : (score >= 40 ? AppTheme.warning : AppTheme.error);

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            CircularPercentIndicator(
              radius: 30,
              lineWidth: 6,
              percent: score / 100,
              center: Text('${score.toInt()}', style: TextStyle(color: color, fontSize: 13, fontWeight: FontWeight.w700)),
              progressColor: color,
              backgroundColor: color.withOpacity(0.15),
              circularStrokeCap: CircularStrokeCap.round,
              animation: true,
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(match['ai_summary'] as String? ?? 'AI match score', maxLines: 2, overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodyMedium),
                  const SizedBox(height: 4),
                  Text('${(match['matched_skills'] as List?)?.length ?? 0} skills matched · '
                      '${(match['gap_skills'] as List?)?.length ?? 0} gaps',
                      style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
