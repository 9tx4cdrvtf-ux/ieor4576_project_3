import { Course, CourseSchedule, DegreeProgress, Preferences, ProfileSummary } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

interface BackendCourse {
  section_key?: string;
  code: string;
  name: string;
  instructor: string;
  credits: number;
  location: string;
  is_online?: boolean;
  time_start: number;
  time_end: number;
  days: string[];
  description_doc: string;
  score?: number;
  requirement_key?: string;
  requirement_label?: string;
  alternatives?: BackendCourse[];
}

interface BackendBucket {
  label: string;
  required_count: number;
  completed_count: number;
  completed_codes: string[];
  remaining_examples?: string[];
  graduation_blocker?: boolean;
}

interface BackendProfile {
  student_id: string;
  name: string;
  program: string;
  program_key: string;
  year?: number;
  graduation_term?: string;
  completed_courses: string[];
  career_tags: string[];
  career_text: string;
  degree_requirements: Record<string, BackendBucket>;
  total_credits: { required: number; completed: number };
}

interface BackendGenerateResponse {
  profile: BackendProfile;
  requirements: Array<{
    key: string;
    label: string;
    remaining: number;
    graduation_blocker: boolean;
    priority: number;
  }>;
  plans: Record<
    string,
    { goal: string; courses: BackendCourse[]; rationale?: string; source?: string }
  >;
  primary_plan_key: string;
  error?: string;
  kind?: string;
}

function decimalHoursToHHMM(d: number): string {
  const h = Math.floor(d);
  const m = Math.round((d - h) * 60);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

function categoryFor(label: string): Course['category'] {
  const l = label.toLowerCase();
  if (l.includes('core') || l.includes('required')) return 'core';
  if (l.includes('breadth') || l.includes('non-ieor')) return 'breadth';
  return 'elective';
}

function backendToCourse(b: BackendCourse, idx: number): Course {
  const schedule: CourseSchedule[] = (b.days || []).map((d) => ({
    day: d as CourseSchedule['day'],
    startTime: decimalHoursToHHMM(b.time_start),
    endTime: decimalHoursToHHMM(b.time_end),
    location: b.location || (b.is_online ? 'Online' : 'TBA'),
  }));

  return {
    id: b.section_key || `${b.code}-${idx}`,
    code: b.code,
    name: b.name,
    credits: b.credits,
    instructor: b.instructor || 'TBA',
    description: b.description_doc?.slice(0, 600) || '',
    reason: b.requirement_label
      ? `Recommended to fulfill ${b.requirement_label}.`
      : 'Recommended to align with your stated preferences.',
    schedule,
    category: categoryFor(b.requirement_label || ''),
    status: 'pending',
    alternatives:
      b.alternatives?.map((a, i) => backendToCourse(a, idx * 100 + i + 1)) || undefined,
    requirementLabel: b.requirement_label,
    score: b.score,
  };
}

export function profileToDegreeProgress(profile: BackendProfile): DegreeProgress[] {
  return Object.values(profile.degree_requirements).map((bucket) => ({
    category: bucket.label,
    completed: bucket.completed_count,
    inProgress: 0,
    remaining: Math.max(0, bucket.required_count - bucket.completed_count),
    total: bucket.required_count,
    courses: bucket.completed_codes,
  }));
}

export async function fetchProfiles(): Promise<ProfileSummary[]> {
  const res = await fetch(`${API_BASE}/api/profiles`);
  if (!res.ok) throw new Error(`profiles ${res.status}`);
  const json = await res.json();
  return json.profiles;
}

export async function fetchProfile(studentId: string): Promise<BackendProfile> {
  const res = await fetch(`${API_BASE}/api/profiles/${encodeURIComponent(studentId)}`);
  if (!res.ok) throw new Error(`profile ${res.status}`);
  return res.json();
}

export async function generateSchedule(prefs: Preferences): Promise<{
  courses: Course[];
  profile: BackendProfile;
  progress: DegreeProgress[];
  rationale?: string;
  source?: string;
  error?: string;
}> {
  const body = {
    student_id: prefs.studentId,
    selected_days: prefs.preferredDays,
    selected_windows: prefs.selectedWindows,
    credit_target: prefs.creditTarget,
    career_text: prefs.careerText,
    career_tags: prefs.careerTags,
    avoid_departments: prefs.avoidDepartments,
    instructor_preference: prefs.instructorPreference || null,
  };
  const res = await fetch(`${API_BASE}/api/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const errJson = await res.json();
      detail = errJson.detail || JSON.stringify(errJson);
    } catch {
      detail = `${res.status} ${await res.text()}`;
    }
    throw new Error(detail);
  }
  const data: BackendGenerateResponse = await res.json();
  if (data.error) {
    return {
      courses: [],
      profile: data.profile ?? ({} as BackendProfile),
      progress: data.profile ? profileToDegreeProgress(data.profile) : [],
      error: data.error,
    };
  }
  const planKey = data.primary_plan_key || 'plan_a';
  const plan = data.plans[planKey];
  return {
    courses: plan.courses.map(backendToCourse),
    profile: data.profile,
    progress: profileToDegreeProgress(data.profile),
    rationale: plan.rationale,
    source: plan.source,
  };
}

export async function streamExplanation(
  studentId: string,
  course: Course,
  fullPlan: Course[],
  careerText: string,
  careerTags: string[],
  onToken: (t: string) => void,
  onDone: () => void,
  onError: (msg: string) => void,
): Promise<void> {
  try {
    const res = await fetch(`${API_BASE}/api/explain/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        student_id: studentId,
        course: { ...course },
        full_plan: fullPlan,
        career_text: careerText,
        career_tags: careerTags,
      }),
    });
    if (!res.body) {
      onError('No response body');
      return;
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop() ?? '';
      for (const ev of events) {
        const line = ev.trim();
        if (!line.startsWith('data:')) continue;
        const payload = line.slice(5).trim();
        if (payload === '[DONE]') {
          onDone();
          return;
        }
        try {
          const obj = JSON.parse(payload);
          if (obj.error) onError(obj.error);
          else if (obj.token) onToken(obj.token);
        } catch {
          // ignore
        }
      }
    }
    onDone();
  } catch (e) {
    onError(String(e));
  }
}
