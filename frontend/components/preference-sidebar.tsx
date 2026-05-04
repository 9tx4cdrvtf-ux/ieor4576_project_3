'use client';

import { useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Sparkles,
  RotateCcw,
  Calendar,
  Clock,
  Briefcase,
  GraduationCap,
  AlertTriangle,
} from 'lucide-react';
import { Preferences, ProfileSummary, TimeWindow } from '@/lib/types';
import {
  careerTagOptions,
  departmentOptions,
  timeWindowOptions,
} from '@/lib/mock-data';

interface PreferenceSidebarProps {
  profiles: ProfileSummary[];
  preferences: Preferences;
  onChange: (next: Preferences) => void;
  onGenerate: () => void;
  onReset: () => void;
  isGenerating: boolean;
}

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];

export function PreferenceSidebar({
  profiles,
  preferences,
  onChange,
  onGenerate,
  onReset,
  isGenerating,
}: PreferenceSidebarProps) {
  const set = (patch: Partial<Preferences>) => onChange({ ...preferences, ...patch });

  const toggleDay = (day: string) =>
    set({
      preferredDays: preferences.preferredDays.includes(day)
        ? preferences.preferredDays.filter((d) => d !== day)
        : [...preferences.preferredDays, day],
    });

  const toggleWindow = (w: TimeWindow) =>
    set({
      selectedWindows: preferences.selectedWindows.includes(w)
        ? preferences.selectedWindows.filter((x) => x !== w)
        : [...preferences.selectedWindows, w],
    });

  const toggleTag = (tag: string) =>
    set({
      careerTags: preferences.careerTags.includes(tag)
        ? preferences.careerTags.filter((t) => t !== tag)
        : [...preferences.careerTags, tag],
    });

  const toggleDept = (dept: string) =>
    set({
      avoidDepartments: preferences.avoidDepartments.includes(dept)
        ? preferences.avoidDepartments.filter((d) => d !== dept)
        : [...preferences.avoidDepartments, dept],
    });

  const dayWarning = useMemo(() => {
    if (preferences.preferredDays.length < 2) return 'Please select at least 2 days.';
    const s = new Set(preferences.preferredDays);
    if (s.size === 2 && s.has('Tuesday') && s.has('Thursday'))
      return 'TTh-only schedules may have limited course availability.';
    return null;
  }, [preferences.preferredDays]);

  const windowWarning =
    preferences.selectedWindows.length === 0 ? 'Please select at least one time window.' : null;

  const creditWarning = useMemo(() => {
    const ratio = preferences.creditTarget / preferences.courseCount;
    if (ratio > 4.5)
      return `${preferences.courseCount} courses typically cover 12–15 credits — consider adding a course or lowering the credit target.`;
    if (preferences.creditTarget > 22) return 'Columbia caps semesters at 22 credits.';
    return null;
  }, [preferences.creditTarget, preferences.courseCount]);

  const isHardBlock = Boolean(dayWarning) || Boolean(windowWarning);
  const blocked = isHardBlock || isGenerating;

  return (
    <aside className="w-full lg:w-80 xl:w-96 flex-shrink-0 space-y-4 overflow-y-auto">
      <Card className="border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <GraduationCap className="h-5 w-5 text-primary" />
            Student Profile
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Label className="text-sm font-medium">Select profile</Label>
          <Select
            value={preferences.studentId}
            onValueChange={(v) => set({ studentId: v })}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Choose a student" />
            </SelectTrigger>
            <SelectContent>
              {profiles.map((p) => (
                <SelectItem key={p.student_id} value={p.student_id}>
                  {p.name} — {p.program}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      <Card className="border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Calendar className="h-5 w-5 text-primary" />
            Schedule Preferences
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="space-y-2">
            <Label className="text-sm font-medium">Preferred Days</Label>
            <div className="flex flex-wrap gap-2">
              {DAYS.map((day) => (
                <button
                  key={day}
                  onClick={() => toggleDay(day)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-full transition-all ${
                    preferences.preferredDays.includes(day)
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                  }`}
                >
                  {day.slice(0, 3)}
                </button>
              ))}
            </div>
            <div className="flex gap-2 mt-1">
              <button
                onClick={() => set({ preferredDays: ['Monday', 'Wednesday', 'Friday'] })}
                className="text-xs underline text-muted-foreground"
              >
                MWF
              </button>
              <button
                onClick={() => set({ preferredDays: ['Tuesday', 'Thursday'] })}
                className="text-xs underline text-muted-foreground"
              >
                TTh
              </button>
            </div>
            {dayWarning && (
              <p className="text-xs text-destructive flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" /> {dayWarning}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label className="text-sm font-medium flex items-center gap-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              Time Windows
            </Label>
            <div className="grid gap-2">
              {timeWindowOptions.map((w) => (
                <label
                  key={w.id}
                  className="flex items-center gap-2 text-sm cursor-pointer"
                >
                  <Checkbox
                    checked={preferences.selectedWindows.includes(w.id)}
                    onCheckedChange={() => toggleWindow(w.id)}
                  />
                  <span className="font-medium">{w.label}</span>
                  <span className="text-xs text-muted-foreground">{w.range}</span>
                </label>
              ))}
            </div>
            {windowWarning && (
              <p className="text-xs text-amber-600 flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" /> {windowWarning}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label className="text-sm font-medium">
              Course Count: {preferences.courseCount}
            </Label>
            <Slider
              value={[preferences.courseCount]}
              onValueChange={(v) => set({ courseCount: v[0] })}
              min={3}
              max={6}
              step={1}
            />
          </div>

          <div className="space-y-2">
            <Label className="text-sm font-medium">
              Credit Target: {preferences.creditTarget}
            </Label>
            <Slider
              value={[preferences.creditTarget]}
              onValueChange={(v) => set({ creditTarget: v[0] })}
              min={12}
              max={22}
              step={1}
            />
            {creditWarning && (
              <p className="text-xs text-amber-600 flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" /> {creditWarning}
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Briefcase className="h-5 w-5 text-primary" />
            Career Goals
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label className="text-sm font-medium">Tags</Label>
            <div className="flex flex-wrap gap-2">
              {careerTagOptions.map((tag) => (
                <button
                  key={tag}
                  onClick={() => toggleTag(tag)}
                  className={`px-3 py-1 text-xs rounded-full ${
                    preferences.careerTags.includes(tag)
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                  }`}
                >
                  {tag}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-sm font-medium">
              Free-text goal (max 200 chars)
            </Label>
            <Textarea
              maxLength={200}
              value={preferences.careerText}
              onChange={(e) => set({ careerText: e.target.value })}
              placeholder="e.g. SWE internship at FAANG, focusing on distributed systems"
              className="resize-none h-20"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-sm font-medium">Instructor preference</Label>
            <Input
              value={preferences.instructorPreference}
              onChange={(e) => set({ instructorPreference: e.target.value })}
              placeholder="e.g. Iyengar"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-sm font-medium">Avoid departments</Label>
            <div className="flex flex-wrap gap-2">
              {departmentOptions.map((d) => (
                <button
                  key={d}
                  onClick={() => toggleDept(d)}
                  className={`px-2.5 py-1 text-xs rounded ${
                    preferences.avoidDepartments.includes(d)
                      ? 'bg-destructive text-destructive-foreground'
                      : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex gap-3 sticky bottom-0 bg-background pt-2 pb-4">
        <Button
          onClick={onGenerate}
          disabled={blocked}
          className="flex-1 gap-2"
          size="lg"
        >
          <Sparkles className="h-4 w-4" />
          {isGenerating ? 'Generating…' : 'Generate Schedule'}
        </Button>
        <Button onClick={onReset} variant="outline" size="lg" className="gap-2">
          <RotateCcw className="h-4 w-4" />
          Reset
        </Button>
      </div>
    </aside>
  );
}
