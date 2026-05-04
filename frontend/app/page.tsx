'use client';

import { useCallback, useEffect, useState } from 'react';
import { PreferenceSidebar } from '@/components/preference-sidebar';
import { DegreeProgress } from '@/components/degree-progress';
import { ScheduleResults } from '@/components/schedule-results';
import {
  Course,
  DegreeProgress as DegreeProgressType,
  Preferences,
  ProfileSummary,
} from '@/lib/types';
import { mockDegreeProgress } from '@/lib/mock-data';
import { fetchProfiles, generateSchedule } from '@/lib/api';
import { GraduationCap } from 'lucide-react';

const DEFAULT_PREFS: Preferences = {
  studentId: 'alex_msor',
  preferredDays: ['Monday', 'Wednesday', 'Friday'],
  selectedWindows: ['morning', 'afternoon'],
  creditTarget: 12,
  careerTags: [],
  careerText: '',
  avoidDepartments: [],
  instructorPreference: '',
};

export default function HomePage() {
  const [profiles, setProfiles] = useState<ProfileSummary[]>([]);
  const [preferences, setPreferences] = useState<Preferences>(DEFAULT_PREFS);
  const [courses, setCourses] = useState<Course[]>([]);
  const [progress, setProgress] = useState<DegreeProgressType[]>(mockDegreeProgress);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rationale, setRationale] = useState<string>('');
  const [planSource, setPlanSource] = useState<string>('');

  useEffect(() => {
    fetchProfiles()
      .then((p) => {
        setProfiles(p);
        if (p.length && !p.find((x) => x.student_id === preferences.studentId)) {
          setPreferences((prev) => ({ ...prev, studentId: p[0].student_id }));
        }
      })
      .catch((e) => setError(`Could not load profiles: ${e}`));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleGenerate = useCallback(async () => {
    setIsGenerating(true);
    setError(null);
    setCourses([]);
    setRationale('');
    setPlanSource('');
    try {
      const result = await generateSchedule(preferences);
      setCourses(result.courses);
      setProgress(result.progress);
      setRationale(result.rationale ?? '');
      setPlanSource(result.source ?? '');
      if (result.error) setError(result.error);
    } catch (e) {
      setError(`${e instanceof Error ? e.message : e}`);
    } finally {
      setIsGenerating(false);
    }
  }, [preferences]);

  const handleReset = useCallback(() => {
    setPreferences(DEFAULT_PREFS);
    setCourses([]);
    setError(null);
  }, []);

  const handleKeep = useCallback((courseId: string) => {
    setCourses((prev) =>
      prev.map((c) => (c.id === courseId ? { ...c, status: 'kept' as const } : c)),
    );
  }, []);

  const handleDelete = useCallback((courseId: string) => {
    setCourses((prev) =>
      prev.map((c) => (c.id === courseId ? { ...c, status: 'deleted' as const } : c)),
    );
  }, []);

  const handleSelectAlternative = useCallback(
    (courseId: string, alternativeId: string) => {
      setCourses((prev) =>
        prev.map((c) => {
          if (c.id === courseId && c.alternatives) {
            const alternative = c.alternatives.find((a) => a.id === alternativeId);
            if (alternative) {
              return {
                ...alternative,
                id: courseId,
                alternatives: [{ ...c, id: alternativeId, alternatives: undefined }],
              };
            }
          }
          return c;
        }),
      );
    },
    [],
  );

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card sticky top-0 z-50">
        <div className="max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-primary flex items-center justify-center">
              <GraduationCap className="h-6 w-6 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-foreground">CourseCompass</h1>
              <p className="text-sm text-muted-foreground">
                AI course planning for Columbia IEOR · Spring 2026
              </p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {error && (
          <div className="mb-4 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive">
            {error}
          </div>
        )}
        <div className="flex flex-col lg:flex-row gap-6">
          <PreferenceSidebar
            profiles={profiles}
            preferences={preferences}
            onChange={setPreferences}
            onGenerate={handleGenerate}
            onReset={handleReset}
            isGenerating={isGenerating}
          />

          <div className="flex-1 min-w-0 space-y-6">
            <DegreeProgress progress={progress} />

            {rationale && (
              <div className="rounded-md border border-primary/30 bg-primary/5 px-4 py-3 text-sm">
                <div className="text-xs font-medium text-primary mb-1">
                  Planner rationale
                </div>
                <p className="text-foreground whitespace-pre-wrap">{rationale}</p>
              </div>
            )}

            <ScheduleResults
              studentId={preferences.studentId}
              courses={courses}
              isGenerating={isGenerating}
              careerText={preferences.careerText}
              careerTags={preferences.careerTags}
              onKeep={handleKeep}
              onDelete={handleDelete}
              onSelectAlternative={handleSelectAlternative}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
