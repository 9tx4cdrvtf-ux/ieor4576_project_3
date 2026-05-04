'use client';

import { Course } from '@/lib/types';
import { cn } from '@/lib/utils';

interface ScheduleCalendarProps {
  courses: Course[];
  onCourseClick: (courseId: string) => void;
}

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'] as const;

function timeToMinutes(time: string): number {
  const [h, m] = time.split(':').map(Number);
  return h * 60 + m;
}

const courseColors = [
  'bg-primary/20 border-primary text-foreground',
  'bg-accent/30 border-accent text-foreground',
  'bg-chart-3/20 border-chart-3 text-foreground',
  'bg-chart-4/20 border-chart-4 text-foreground',
  'bg-chart-5/20 border-chart-5 text-foreground',
];

export function ScheduleCalendar({ courses, onCourseClick }: ScheduleCalendarProps) {
  const activeCourses = courses.filter((c) => c.status !== 'deleted');

  // Compute the time range we need to render. Default 8-21; tighten to fit
  // actual blocks plus a 30-min pad.
  let earliest = 8 * 60;
  let latest = 18 * 60;
  for (const c of activeCourses) {
    for (const slot of c.schedule) {
      earliest = Math.min(earliest, timeToMinutes(slot.startTime));
      latest = Math.max(latest, timeToMinutes(slot.endTime));
    }
  }
  earliest = Math.floor((earliest - 30) / 60) * 60;
  latest = Math.ceil((latest + 30) / 60) * 60;
  const spanMinutes = latest - earliest;
  const PIXELS_PER_HOUR = 60;
  const totalHeight = (spanMinutes / 60) * PIXELS_PER_HOUR;

  const hours: number[] = [];
  for (let m = earliest; m < latest; m += 60) hours.push(m / 60);

  function getEventStyle(startTime: string, endTime: string) {
    const top = ((timeToMinutes(startTime) - earliest) / 60) * PIXELS_PER_HOUR;
    const height = ((timeToMinutes(endTime) - timeToMinutes(startTime)) / 60) * PIXELS_PER_HOUR;
    return { top: `${top}px`, height: `${Math.max(height, 30)}px` };
  }

  const fmtHour = (h: number) =>
    h === 0 ? '12AM' : h < 12 ? `${h}AM` : h === 12 ? '12PM' : `${h - 12}PM`;

  return (
    <div className="bg-card rounded-lg border border-border overflow-hidden">
      <div className="grid grid-cols-[60px_repeat(5,1fr)] border-b border-border">
        <div className="p-2 bg-muted/50" />
        {DAYS.map((day) => (
          <div
            key={day}
            className="p-3 text-center text-sm font-medium bg-muted/50 border-l border-border"
          >
            {day}
          </div>
        ))}
      </div>

      <div
        className="grid grid-cols-[60px_repeat(5,1fr)]"
        style={{ height: `${totalHeight}px` }}
      >
        <div className="relative">
          {hours.map((h) => (
            <div
              key={h}
              className="h-[60px] flex items-start justify-end pr-2 text-xs text-muted-foreground border-b border-border/50"
            >
              {fmtHour(h)}
            </div>
          ))}
        </div>

        {DAYS.map((day) => (
          <div key={day} className="relative border-l border-border">
            {hours.map((h) => (
              <div key={h} className="h-[60px] border-b border-border/50" />
            ))}

            {activeCourses.map((course, courseIndex) =>
              course.schedule
                .filter((s) => s.day === day)
                .map((slot, slotIndex) => (
                  <button
                    key={`${course.id}-${slotIndex}`}
                    onClick={() => onCourseClick(course.id)}
                    className={cn(
                      'absolute left-1 right-1 rounded-md border-l-4 px-2 py-1 text-left transition-all hover:shadow-md',
                      courseColors[courseIndex % courseColors.length],
                      course.status === 'pending' ? 'opacity-60' : 'opacity-100',
                    )}
                    style={getEventStyle(slot.startTime, slot.endTime)}
                  >
                    <p className="text-xs font-semibold truncate text-foreground">
                      {course.code}
                    </p>
                    <p className="text-[10px] truncate text-muted-foreground">
                      {slot.startTime} – {slot.endTime}
                    </p>
                    <p className="text-[10px] truncate text-muted-foreground">
                      {slot.location}
                    </p>
                  </button>
                )),
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
