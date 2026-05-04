import { Course, DegreeProgress, TimeWindow } from './types';

// Used only as a placeholder before the user has run the agent pipeline.
export const mockDegreeProgress: DegreeProgress[] = [
  {
    category: 'Required Core',
    completed: 3,
    inProgress: 0,
    remaining: 1,
    total: 4,
    courses: ['IEOR4004', 'IEOR4106', 'IEOR4500'],
  },
  {
    category: 'IEOR Electives',
    completed: 3,
    inProgress: 0,
    remaining: 2,
    total: 5,
    courses: ['IEOR4307', 'IEOR4720', 'IEOR4511'],
  },
  {
    category: 'Approved Non-IEOR Electives',
    completed: 0,
    inProgress: 0,
    remaining: 2,
    total: 2,
    courses: [],
  },
];

export const mockGeneratedCourses: Course[] = [];

export const careerTagOptions = [
  'Software Engineer',
  'ML Engineer',
  'Data Scientist',
  'Quant',
  'Product Manager',
  'Research',
  'Consulting',
  'Finance',
  'Startup',
];

export const focusAreaOptions = [
  'Machine Learning',
  'Optimization',
  'Stochastic Modeling',
  'Cloud Computing',
  'Data Engineering',
  'Risk & Derivatives',
  'Supply Chain',
  'Statistics',
];

export const timeWindowOptions: { id: TimeWindow; label: string; range: string }[] = [
  { id: 'early_morning', label: 'Early Morning', range: '08:00 – 10:00' },
  { id: 'morning', label: 'Morning', range: '10:10 – 12:00' },
  { id: 'afternoon', label: 'Afternoon', range: '12:10 – 16:00' },
  { id: 'late_afternoon', label: 'Late Afternoon', range: '16:10 – 18:00' },
  { id: 'evening', label: 'Evening', range: '18:10 – 21:00' },
];

export const departmentOptions = [
  'IEOR',
  'COMS',
  'STAT',
  'ECON',
  'MATH',
  'B8',
  'EEOR',
];
