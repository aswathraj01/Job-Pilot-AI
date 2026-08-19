import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';

// ── Models ────────────────────────────────────────────────────────────────────

class JobSummary {
  final String id;
  final String url;
  final String status;
  final String? title;
  final String? company;
  final String? location;
  final String? remoteType;
  final String? jobType;
  final double? salaryMin;
  final double? salaryMax;
  final String? currency;
  final List<String>? skillsRequired;
  final String? sourcePlatform;
  final DateTime createdAt;
  final DateTime? appliedAt;
  final DateTime? deadline;

  const JobSummary({
    required this.id,
    required this.url,
    required this.status,
    this.title,
    this.company,
    this.location,
    this.remoteType,
    this.jobType,
    this.salaryMin,
    this.salaryMax,
    this.currency,
    this.skillsRequired,
    this.sourcePlatform,
    required this.createdAt,
    this.appliedAt,
    this.deadline,
  });

  factory JobSummary.fromJson(Map<String, dynamic> json) => JobSummary(
        id: json['id'] as String,
        url: json['url'] as String,
        status: json['status'] as String,
        title: json['title'] as String?,
        company: json['company'] as String?,
        location: json['location'] as String?,
        remoteType: json['remote_type'] as String?,
        jobType: json['job_type'] as String?,
        salaryMin: (json['salary_min'] as num?)?.toDouble(),
        salaryMax: (json['salary_max'] as num?)?.toDouble(),
        currency: json['currency'] as String?,
        skillsRequired: (json['skills_required'] as List?)?.cast<String>(),
        sourcePlatform: json['source_platform'] as String?,
        createdAt: DateTime.parse(json['created_at'] as String),
        appliedAt: json['applied_at'] != null ? DateTime.parse(json['applied_at'] as String) : null,
        deadline: json['deadline'] != null ? DateTime.parse(json['deadline'] as String) : null,
      );

  String get salaryRange {
    if (salaryMin == null && salaryMax == null) return 'Not specified';
    final curr = currency ?? 'USD';
    if (salaryMin != null && salaryMax != null) {
      return '\$${_fmt(salaryMin!)} – \$${_fmt(salaryMax!)} $curr';
    }
    return '\$${_fmt(salaryMin ?? salaryMax!)} $curr';
  }

  String _fmt(double v) => v >= 1000 ? '${(v / 1000).toStringAsFixed(0)}k' : v.toStringAsFixed(0);
}

class JobsListResult {
  final List<JobSummary> items;
  final int total;
  final int page;
  final bool hasNext;

  const JobsListResult({required this.items, required this.total, required this.page, required this.hasNext});
}

// ── Repository ────────────────────────────────────────────────────────────────

class JobsRepository {
  final Dio _dio;
  const JobsRepository(this._dio);

  Future<JobsListResult> listJobs({
    int page = 1,
    int pageSize = 20,
    String? status,
    String? company,
    String? search,
    String? remoteType,
  }) async {
    final params = <String, dynamic>{
      'page': page,
      'page_size': pageSize,
      if (status != null) 'status': status,
      if (company != null) 'company': company,
      if (search != null && search.isNotEmpty) 'search': search,
      if (remoteType != null) 'remote_type': remoteType,
    };
    final resp = await _dio.get('/jobs/', queryParameters: params);
    final data = resp.data as Map<String, dynamic>;
    return JobsListResult(
      items: (data['items'] as List).map((j) => JobSummary.fromJson(j as Map<String, dynamic>)).toList(),
      total: data['total'] as int,
      page: data['page'] as int,
      hasNext: data['has_next'] as bool,
    );
  }

  Future<Map<String, dynamic>> getJobDetail(String id) async {
    final resp = await _dio.get('/jobs/$id');
    return resp.data as Map<String, dynamic>;
  }

  Future<JobSummary> createJob(String url, {String status = 'saved'}) async {
    final resp = await _dio.post('/jobs/', data: {'url': url, 'status': status});
    return JobSummary.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<JobSummary> updateJobStatus(String id, String status) async {
    final resp = await _dio.patch('/jobs/$id', data: {'status': status});
    return JobSummary.fromJson(resp.data as Map<String, dynamic>);
  }

  Future<void> deleteJob(String id) async {
    await _dio.delete('/jobs/$id');
  }

  Future<Map<String, dynamic>> addNote(String jobId, String content) async {
    final resp = await _dio.post('/jobs/$jobId/notes', data: {'content': content});
    return resp.data as Map<String, dynamic>;
  }

  Future<void> deleteNote(String jobId, String noteId) async {
    await _dio.delete('/jobs/$jobId/notes/$noteId');
  }

  Future<Map<String, dynamic>> addReminder(String jobId, String message, DateTime remindAt) async {
    final resp = await _dio.post('/jobs/$jobId/reminders', data: {
      'message': message,
      'remind_at': remindAt.toUtc().toIso8601String(),
    });
    return resp.data as Map<String, dynamic>;
  }
}

final jobsRepositoryProvider = Provider<JobsRepository>((ref) {
  return JobsRepository(ref.watch(dioProvider));
});

// ── State Providers ───────────────────────────────────────────────────────────

class JobsFilter {
  final String? status;
  final String? search;
  final String? remoteType;

  const JobsFilter({this.status, this.search, this.remoteType});

  JobsFilter copyWith({String? status, String? search, String? remoteType, bool clearStatus = false}) {
    return JobsFilter(
      status: clearStatus ? null : (status ?? this.status),
      search: search ?? this.search,
      remoteType: remoteType ?? this.remoteType,
    );
  }
}

final jobsFilterProvider = StateProvider<JobsFilter>((ref) => const JobsFilter());

final jobsListProvider = FutureProvider.autoDispose<JobsListResult>((ref) async {
  final repo = ref.watch(jobsRepositoryProvider);
  final filter = ref.watch(jobsFilterProvider);
  return repo.listJobs(
    status: filter.status,
    search: filter.search,
    remoteType: filter.remoteType,
  );
});

final jobDetailProvider = FutureProvider.autoDispose.family<Map<String, dynamic>, String>((ref, id) async {
  return ref.watch(jobsRepositoryProvider).getJobDetail(id);
});
