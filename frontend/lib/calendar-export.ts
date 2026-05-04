import { Course } from './types';

// Columbia Spring 2026 semester window.
const SEMESTER_START = new Date('2026-01-20T00:00:00');
const SEMESTER_END = new Date('2026-05-04T00:00:00');

function formatDateForICS(date: Date): string {
  return date.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';
}

function getNextDayOfWeek(dayName: string): Date {
  const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const target = days.indexOf(dayName);
  const start = new Date(SEMESTER_START);
  while (start.getDay() !== target) {
    start.setDate(start.getDate() + 1);
  }
  return start;
}

function semesterWeekCount(): number {
  const ms = SEMESTER_END.getTime() - SEMESTER_START.getTime();
  return Math.ceil(ms / (7 * 24 * 60 * 60 * 1000));
}

function parseTime(timeStr: string): { hours: number; minutes: number } {
  const [hours, minutes] = timeStr.split(':').map(Number);
  return { hours, minutes };
}

export function generateICSFile(courses: Course[]): string {
  const keptCourses = courses.filter(c => c.status === 'kept');
  
  let icsContent = `BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AI Course Advisor//Course Schedule//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:Course Schedule
`;

  keptCourses.forEach(course => {
    course.schedule.forEach(slot => {
      const eventDate = getNextDayOfWeek(slot.day);
      const startTime = parseTime(slot.startTime);
      const endTime = parseTime(slot.endTime);
      
      const startDate = new Date(eventDate);
      startDate.setHours(startTime.hours, startTime.minutes, 0, 0);
      
      const endDate = new Date(eventDate);
      endDate.setHours(endTime.hours, endTime.minutes, 0, 0);

      icsContent += `BEGIN:VEVENT
DTSTART:${formatDateForICS(startDate)}
DTEND:${formatDateForICS(endDate)}
RRULE:FREQ=WEEKLY;COUNT=${semesterWeekCount()}
SUMMARY:${course.code} - ${course.name}
DESCRIPTION:${course.description.replace(/\n/g, '\\n')}\\n\\nInstructor: ${course.instructor}
LOCATION:${slot.location}
UID:${course.id}-${slot.day}-${Date.now()}@courseadvisor
END:VEVENT
`;
    });
  });

  icsContent += 'END:VCALENDAR';
  return icsContent;
}

export function downloadICSFile(courses: Course[], studentName: string = 'Schedule') {
  const icsContent = generateICSFile(courses);
  const blob = new Blob([icsContent], { type: 'text/calendar;charset=utf-8' });
  const url = URL.createObjectURL(blob);

  const safe = studentName.replace(/[^A-Za-z0-9]+/g, '');
  const link = document.createElement('a');
  link.href = url;
  link.download = `CourseCompass_Spring2026_${safe || 'Schedule'}.ics`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function generateGoogleCalendarUrl(course: Course): string {
  const slot = course.schedule[0];
  if (!slot) return '';
  
  const eventDate = getNextDayOfWeek(slot.day);
  const startTime = parseTime(slot.startTime);
  const endTime = parseTime(slot.endTime);
  
  const startDate = new Date(eventDate);
  startDate.setHours(startTime.hours, startTime.minutes, 0, 0);
  
  const endDate = new Date(eventDate);
  endDate.setHours(endTime.hours, endTime.minutes, 0, 0);

  const formatForGoogle = (d: Date) => d.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
  
  const params = new URLSearchParams({
    action: 'TEMPLATE',
    text: `${course.code} - ${course.name}`,
    dates: `${formatForGoogle(startDate)}/${formatForGoogle(endDate)}`,
    details: `${course.description}\n\nInstructor: ${course.instructor}`,
    location: slot.location,
    recur: `RRULE:FREQ=WEEKLY;COUNT=${semesterWeekCount()}`,
  });

  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}
