export interface Course {
  id: string;
  code: string;
  name: string;
  credits: number;
  instructor: string;
  description: string;
  reason: string;
  schedule: CourseSchedule[];
  category: 'core' | 'elective' | 'breadth';
  status: 'pending' | 'kept' | 'deleted';
  alternatives?: Course[];
  requirementLabel?: string;
  score?: number;
}

export interface CourseSchedule {
  day: 'Monday' | 'Tuesday' | 'Wednesday' | 'Thursday' | 'Friday';
  startTime: string;
  endTime: string;
  location: string;
}

export interface DegreeProgress {
  category: string;
  completed: number;
  inProgress: number;
  remaining: number;
  total: number;
  courses: string[];
}

export type TimeWindow =
  | 'early_morning'
  | 'morning'
  | 'afternoon'
  | 'late_afternoon'
  | 'evening';

export interface Preferences {
  studentId: string;
  preferredDays: string[];
  selectedWindows: TimeWindow[];
  courseCount: number;
  creditTarget: number;
  careerTags: string[];
  careerText: string;
  avoidDepartments: string[];
  instructorPreference: string;
}

export interface ProfileSummary {
  student_id: string;
  name: string;
  program: string;
  year?: number;
  graduation_term?: string;
  completed_credits?: number;
  required_credits?: number;
}
