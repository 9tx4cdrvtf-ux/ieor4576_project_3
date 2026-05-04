'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Calendar, Download, ExternalLink, Grid3X3, List } from 'lucide-react';
import { Course } from '@/lib/types';
import { ScheduleCalendar } from './schedule-calendar';
import { CourseCard } from './course-card';
import { downloadICSFile, generateGoogleCalendarUrl } from '@/lib/calendar-export';

interface ScheduleResultsProps {
  studentId: string;
  courses: Course[];
  onKeep: (courseId: string) => void;
  onDelete: (courseId: string) => void;
  onSelectAlternative: (courseId: string, alternativeId: string) => void;
}

export function ScheduleResults({
  studentId,
  courses,
  onKeep,
  onDelete,
  onSelectAlternative,
}: ScheduleResultsProps) {
  const [highlightedCourse, setHighlightedCourse] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'calendar' | 'list'>('calendar');

  const keptCourses = courses.filter((c) => c.status === 'kept');
  const totalCredits = courses
    .filter((c) => c.status !== 'deleted')
    .reduce((acc, c) => acc + c.credits, 0);
  const keptCredits = keptCourses.reduce((acc, c) => acc + c.credits, 0);

  const handleExportAppleCalendar = () => {
    downloadICSFile(courses);
  };

  const handleExportGoogleCalendar = () => {
    keptCourses.forEach((course) => {
      const url = generateGoogleCalendarUrl(course);
      window.open(url, '_blank');
    });
  };

  if (courses.length === 0) {
    return (
      <Card className="border-border/50 h-[400px] flex items-center justify-center">
        <div className="text-center space-y-3">
          <Calendar className="h-12 w-12 mx-auto text-muted-foreground/50" />
          <div>
            <p className="text-lg font-medium text-foreground">No Schedule Generated</p>
            <p className="text-sm text-muted-foreground">
              Set your preferences and click &quot;Generate Schedule&quot; to get started
            </p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card className="border-border/50">
        <CardHeader className="pb-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Calendar className="h-5 w-5 text-primary" />
                Generated Schedule
              </CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                {keptCredits}/{totalCredits} credits confirmed
              </p>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <div className="flex items-center rounded-lg border border-border p-1">
                <button
                  onClick={() => setViewMode('calendar')}
                  className={`p-2 rounded-md transition-colors ${
                    viewMode === 'calendar'
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <Grid3X3 className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setViewMode('list')}
                  className={`p-2 rounded-md transition-colors ${
                    viewMode === 'list'
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <List className="h-4 w-4" />
                </button>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleExportGoogleCalendar}
                disabled={keptCourses.length === 0}
                className="gap-2"
              >
                <ExternalLink className="h-4 w-4" />
                Google Calendar
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleExportAppleCalendar}
                disabled={keptCourses.length === 0}
                className="gap-2"
              >
                <Download className="h-4 w-4" />
                Apple Calendar
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {viewMode === 'calendar' ? (
            <div className="overflow-x-auto">
              <ScheduleCalendar
                courses={courses}
                onCourseClick={setHighlightedCourse}
              />
            </div>
          ) : (
            <div className="space-y-2">
              {courses
                .filter((c) => c.status !== 'deleted')
                .map((course) => (
                  <div
                    key={course.id}
                    className="flex items-center justify-between p-3 bg-secondary/50 rounded-lg"
                  >
                    <div>
                      <p className="font-medium">{course.code}</p>
                      <p className="text-sm text-muted-foreground">{course.name}</p>
                    </div>
                    <div className="text-right text-sm text-muted-foreground">
                      {course.schedule.map((s) => s.day.slice(0, 3)).join(', ')}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div>
        <h3 className="text-lg font-semibold mb-4">Course Details</h3>
        <div className="grid gap-4 md:grid-cols-2">
          {courses
            .filter((c) => c.status !== 'deleted')
            .map((course) => (
              <CourseCard
                key={course.id}
                course={course}
                studentId={studentId}
                fullPlan={courses.filter((c) => c.status !== 'deleted')}
                onKeep={onKeep}
                onDelete={onDelete}
                onSelectAlternative={onSelectAlternative}
                isHighlighted={highlightedCourse === course.id}
              />
            ))}
        </div>
      </div>
    </div>
  );
}
