import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'dart:convert';

import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/glass_card.dart';
import '../../../shared/widgets/gradient_button.dart';
import '../data/jobs_repository.dart';

class AddJobPage extends ConsumerStatefulWidget {
  const AddJobPage({super.key});

  @override
  ConsumerState<AddJobPage> createState() => _AddJobPageState();
}

class _AddJobPageState extends ConsumerState<AddJobPage> {
  final _urlCtrl = TextEditingController();
  bool _isSubmitting = false;
  String? _processingJobId;
  String _processingStatus = '';
  int _progress = 0;
  String? _errorMsg;

  // WebSocket channel for real-time status
  WebSocketChannel? _wsChannel;

  static const _supportedPlatforms = [
    ('LinkedIn', 'linkedin.com'),
    ('Indeed', 'indeed.com'),
    ('Greenhouse', 'greenhouse.io'),
    ('Lever', 'lever.co'),
    ('Workday', 'workday.com'),
    ('Ashby', 'ashbyhq.com'),
    ('Wellfound', 'wellfound.com'),
    ('Any job board URL', ''),
  ];

  @override
  void dispose() {
    _urlCtrl.dispose();
    _wsChannel?.sink.close();
    super.dispose();
  }

  Future<void> _submitUrl() async {
    final url = _urlCtrl.text.trim();
    if (url.isEmpty || !url.startsWith('http')) {
      setState(() => _errorMsg = 'Please enter a valid URL starting with http(s)://');
      return;
    }

    setState(() {
      _isSubmitting = true;
      _errorMsg = null;
      _processingStatus = 'Queueing...';
      _progress = 5;
    });

    try {
      final repo = ref.read(jobsRepositoryProvider);
      final job = await repo.createJob(url);

      setState(() {
        _processingJobId = job.id;
        _processingStatus = 'Connecting...';
        _progress = 10;
      });

      // Connect WebSocket for real-time updates
      _connectWebSocket(job.id);

    } catch (e) {
      setState(() {
        _isSubmitting = false;
        _errorMsg = e.toString().replaceAll('DioException', '').trim();
      });
    }
  }

  void _connectWebSocket(String jobId) {
    const wsUrl = String.fromEnvironment('WS_URL', defaultValue: 'ws://localhost:8000/api/v1');
    // Token from storage would be appended in production
    _wsChannel = WebSocketChannel.connect(Uri.parse('$wsUrl/jobs/$jobId/ws'));

    _wsChannel!.stream.listen(
      (data) {
        final msg = jsonDecode(data as String) as Map<String, dynamic>;
        final status = msg['status'] as String? ?? '';
        final message = msg['message'] as String? ?? '';
        final progress = msg['progress'] as int? ?? 0;

        setState(() {
          _processingStatus = message;
          _progress = progress;
        });

        if (status == 'done') {
          _wsChannel?.sink.close();
          // Invalidate cache and navigate to job detail
          ref.invalidate(jobsListProvider);
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('✅ Job details extracted successfully!'),
                backgroundColor: AppTheme.success,
              ),
            );
            context.go('/jobs/$jobId');
          }
        } else if (status == 'failed') {
          _wsChannel?.sink.close();
          setState(() {
            _isSubmitting = false;
            _errorMsg = 'Processing failed. The job was saved but details could not be extracted.';
          });
          if (mounted) context.go('/jobs/$jobId');
        }
      },
      onError: (e) => setState(() {
        _processingStatus = 'Processing in background...';
      }),
    );
  }

  Future<void> _pasteFromClipboard() async {
    final data = await Clipboard.getData('text/plain');
    if (data?.text != null) {
      _urlCtrl.text = data!.text!;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: const Text('Track New Job'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/jobs'),
        ),
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(32),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 680),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildHeroSection(context)
                    .animate()
                    .fadeIn(duration: 400.ms)
                    .slideY(begin: -0.1),
                const SizedBox(height: 40),
                GlassCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      if (!_isSubmitting) ...[
                        _buildUrlInput(),
                        const SizedBox(height: 24),
                        GradientButton(
                          onPressed: _submitUrl,
                          child: const Text('Extract & Track Job'),
                        ),
                      ] else ...[
                        _buildProcessingView(),
                      ],
                      if (_errorMsg != null) ...[
                        const SizedBox(height: 16),
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: AppTheme.error.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: AppTheme.error.withOpacity(0.3)),
                          ),
                          child: Text(_errorMsg!, style: const TextStyle(color: AppTheme.error, fontSize: 14)),
                        ),
                      ],
                    ],
                  ),
                ).animate().fadeIn(delay: 200.ms, duration: 400.ms).slideY(begin: 0.05),
                const SizedBox(height: 32),
                _buildSupportedPlatforms(context)
                    .animate(delay: 400.ms)
                    .fadeIn(duration: 400.ms),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeroSection(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                gradient: AppGradients.primaryGradient,
                borderRadius: BorderRadius.circular(14),
                boxShadow: [BoxShadow(color: AppTheme.primary.withOpacity(0.4), blurRadius: 16)],
              ),
              child: const Icon(Icons.auto_awesome, color: Colors.white, size: 26),
            ),
            const SizedBox(width: 16),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('AI Job Extraction', style: Theme.of(context).textTheme.headlineMedium),
                Text('Powered by Gemini 1.5 Flash', style: Theme.of(context).textTheme.bodyMedium),
              ],
            ),
          ],
        ),
        const SizedBox(height: 16),
        Text(
          'Paste any job posting URL. Our AI will extract the title, company, salary, required skills, benefits, '
          'and every other detail — automatically.',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppTheme.textSecondary),
        ),
      ],
    );
  }

  Widget _buildUrlInput() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Job Posting URL', style: Theme.of(context).textTheme.labelLarge),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: TextFormField(
                controller: _urlCtrl,
                decoration: InputDecoration(
                  hintText: 'https://linkedin.com/jobs/view/...',
                  prefixIcon: const Icon(Icons.link_rounded, size: 18),
                  suffixIcon: IconButton(
                    icon: const Icon(Icons.content_paste_rounded, size: 18),
                    tooltip: 'Paste from clipboard',
                    onPressed: _pasteFromClipboard,
                  ),
                ),
                keyboardType: TextInputType.url,
                onFieldSubmitted: (_) => _submitUrl(),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildProcessingView() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        const SizedBox(height: 12),
        // Animated icon
        Container(
          width: 72,
          height: 72,
          decoration: BoxDecoration(
            color: AppTheme.primary.withOpacity(0.1),
            borderRadius: BorderRadius.circular(20),
          ),
          child: const Icon(Icons.auto_awesome, color: AppTheme.primary, size: 36),
        ).animate(onPlay: (c) => c.repeat()).shimmer(duration: 1200.ms, color: AppTheme.primaryLight),
        const SizedBox(height: 20),
        Text(
          'AI is extracting job details...',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        Text(
          _processingStatus,
          style: Theme.of(context).textTheme.bodyMedium,
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 24),
        // Progress bar
        ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: LinearProgressIndicator(
            value: _progress / 100,
            backgroundColor: AppTheme.surfaceVariant,
            valueColor: const AlwaysStoppedAnimation<Color>(AppTheme.primary),
            minHeight: 6,
          ),
        ),
        const SizedBox(height: 8),
        Text('$_progress%', style: Theme.of(context).textTheme.bodySmall),
        const SizedBox(height: 12),
        // Steps
        ..._buildProcessingSteps(),
        const SizedBox(height: 8),
      ],
    );
  }

  List<Widget> _buildProcessingSteps() {
    final steps = [
      (5, 'Queued for processing'),
      (20, 'Fetching job page'),
      (55, 'Running AI extraction'),
      (80, 'Saving job details'),
      (100, 'Complete!'),
    ];

    return steps.map((step) {
      final (threshold, label) = step;
      final isDone = _progress >= threshold;
      final isActive = _progress >= threshold - 30 && _progress < threshold;
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          children: [
            Icon(
              isDone ? Icons.check_circle_rounded : (isActive ? Icons.radio_button_on : Icons.radio_button_off),
              size: 16,
              color: isDone ? AppTheme.success : (isActive ? AppTheme.primary : AppTheme.textMuted),
            ),
            const SizedBox(width: 8),
            Text(
              label,
              style: TextStyle(
                color: isDone ? AppTheme.textPrimary : AppTheme.textMuted,
                fontSize: 13,
                fontWeight: isDone ? FontWeight.w500 : FontWeight.w400,
              ),
            ),
          ],
        ),
      );
    }).toList();
  }

  Widget _buildSupportedPlatforms(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Supported Platforms', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: _supportedPlatforms
              .where((p) => p.$2.isNotEmpty)
              .map((p) => Chip(
                    label: Text(p.$1),
                    avatar: const Icon(Icons.language, size: 14),
                  ))
              .toList(),
        ),
      ],
    );
  }
}
