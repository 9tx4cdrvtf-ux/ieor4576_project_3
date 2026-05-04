'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Check, X, Clock, MapPin, User, BookOpen, RefreshCw, Sparkles } from 'lucide-react';
import { Course } from '@/lib/types';
import { cn } from '@/lib/utils';
import { streamExplanation } from '@/lib/api';

interface CourseCardProps {
  course: Course;
  studentId: string;
  fullPlan: Course[];
  onKeep: (courseId: string) => void;
  onDelete: (courseId: string) => void;
  onSelectAlternative: (courseId: string, alternativeId: string) => void;
  isHighlighted?: boolean;
}

export function CourseCard({
  course,
  studentId,
  fullPlan,
  onKeep,
  onDelete,
  onSelectAlternative,
  isHighlighted,
}: CourseCardProps) {
  const [streamed, setStreamed] = useState<string>('');
  const [streaming, setStreaming] = useState(false);

  const handleStreamExplain = () => {
    setStreamed('');
    setStreaming(true);
    streamExplanation(
      studentId,
      course,
      fullPlan,
      (token) => setStreamed((s) => s + token),
      () => setStreaming(false),
      (msg) => {
        setStreamed((s) => s + `\n[error] ${msg}`);
        setStreaming(false);
      },
    );
  };

  const categoryColors = {
    core: 'bg-primary/10 text-primary border-primary/20',
    elective: 'bg-accent/20 text-accent-foreground border-accent/30',
    breadth: 'bg-chart-3/10 text-chart-3 border-chart-3/20',
  };

  return (
    <Card
      className={cn(
        'transition-all duration-300 border-border/50',
        course.status === 'pending' && 'opacity-70',
        course.status === 'kept' && 'ring-2 ring-primary shadow-md',
        course.status === 'deleted' && 'opacity-40 grayscale',
        isHighlighted && 'ring-2 ring-accent shadow-lg'
      )}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <CardTitle className="text-lg">{course.code}</CardTitle>
              <Badge variant="outline" className={categoryColors[course.category]}>
                {course.category}
              </Badge>
              <Badge variant="secondary">{course.credits} credits</Badge>
            </div>
            <h4 className="font-medium text-foreground">{course.name}</h4>
          </div>
          {course.status === 'kept' && (
            <div className="flex-shrink-0 h-8 w-8 rounded-full bg-primary flex items-center justify-center">
              <Check className="h-4 w-4 text-primary-foreground" />
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <User className="h-4 w-4" />
            <span>{course.instructor}</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <MapPin className="h-4 w-4" />
            <span>{course.schedule[0]?.location}</span>
          </div>
          <div className="col-span-2 flex items-center gap-2 text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span>
              {course.schedule.map((s) => `${s.day.slice(0, 3)} ${s.startTime}-${s.endTime}`).join(', ')}
            </span>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm font-medium">
            <BookOpen className="h-4 w-4 text-primary" />
            Description
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">
            {course.description}
          </p>
        </div>

        <div className="space-y-2 p-3 bg-primary/5 rounded-lg border border-primary/10">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-primary">Why this course?</p>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 gap-1 text-xs"
              onClick={handleStreamExplain}
              disabled={streaming}
            >
              <Sparkles className="h-3 w-3" />
              {streaming ? 'Explaining…' : 'Explain'}
            </Button>
          </div>
          <p className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">
            {streamed || course.reason}
          </p>
        </div>

        {course.alternatives && course.alternatives.length > 0 && (
          <div className="space-y-2 p-3 bg-secondary rounded-lg">
            <div className="flex items-center gap-2 text-sm font-medium">
              <RefreshCw className="h-4 w-4 text-muted-foreground" />
              Alternative Section Available
            </div>
            {course.alternatives.map((alt) => (
              <div key={alt.id} className="text-sm text-muted-foreground">
                <p className="font-medium text-foreground">{alt.instructor}</p>
                <p className="text-xs">
                  {alt.schedule.map((s) => `${s.day.slice(0, 3)} ${s.startTime}-${s.endTime}`).join(', ')}
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2 w-full"
                  onClick={() => onSelectAlternative(course.id, alt.id)}
                >
                  Switch to this section
                </Button>
              </div>
            ))}
          </div>
        )}

        <div className="flex gap-2 pt-2">
          <Button
            onClick={() => onKeep(course.id)}
            disabled={course.status === 'kept'}
            className="flex-1 gap-2"
            variant={course.status === 'kept' ? 'secondary' : 'default'}
          >
            <Check className="h-4 w-4" />
            {course.status === 'kept' ? 'Kept' : 'Keep'}
          </Button>
          <Button
            onClick={() => onDelete(course.id)}
            variant="outline"
            className="flex-1 gap-2 text-destructive hover:text-destructive"
          >
            <X className="h-4 w-4" />
            Delete
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
