'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { GraduationCap, Info, Flag } from 'lucide-react';
import { DegreeProgress as DegreeProgressType } from '@/lib/types';

interface DegreeProgressProps {
  progress: DegreeProgressType[];
}

export function DegreeProgress({ progress }: DegreeProgressProps) {
  const totalCredits = progress.reduce((acc, p) => acc + p.total * 3, 0);
  const completedCredits = progress.reduce((acc, p) => acc + p.completed * 3, 0);
  const inProgressCredits = progress.reduce((acc, p) => acc + p.inProgress * 3, 0);
  
  const milestones = [
    { name: 'Core Requirements', completed: true },
    { name: 'Track Declaration', completed: true },
    { name: 'Thesis Proposal', completed: false },
  ];
  const completedMilestones = milestones.filter(m => m.completed).length;

  return (
    <Card className="border-border/50">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <GraduationCap className="h-5 w-5 text-primary" />
            Degree Progress
          </CardTitle>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <button className="text-muted-foreground hover:text-foreground transition-colors">
                  <Info className="h-4 w-4" />
                </button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Based on your official transcript</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">All Courses</span>
            <span className="text-muted-foreground">
              {completedCredits + inProgressCredits}/{totalCredits} credits
            </span>
          </div>
          
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="relative h-3 bg-secondary rounded-full overflow-hidden cursor-pointer">
                  <div
                    className="absolute left-0 top-0 h-full bg-primary transition-all duration-500"
                    style={{ width: `${(completedCredits / totalCredits) * 100}%` }}
                  />
                  <div
                    className="absolute top-0 h-full bg-accent transition-all duration-500"
                    style={{ 
                      left: `${(completedCredits / totalCredits) * 100}%`,
                      width: `${(inProgressCredits / totalCredits) * 100}%` 
                    }}
                  />
                </div>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                <div className="space-y-2">
                  <p className="font-medium">Completed Courses:</p>
                  <ul className="text-xs space-y-1">
                    {progress.flatMap(p => p.courses.slice(0, p.completed)).map(course => (
                      <li key={course} className="text-muted-foreground">{course}</li>
                    ))}
                  </ul>
                </div>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
          
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-primary" />
              <span>{progress.reduce((acc, p) => acc + p.completed, 0)} Completed</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-accent" />
              <span>{progress.reduce((acc, p) => acc + p.inProgress, 0)} In Progress</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-secondary" />
              <span>{progress.reduce((acc, p) => acc + p.remaining, 0)} Remaining</span>
            </div>
          </div>
        </div>

        <div className="border-t border-border pt-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Flag className="h-4 w-4 text-muted-foreground" />
              Milestones
            </div>
            <span className="text-xs text-muted-foreground">
              {completedMilestones}/{milestones.length}
            </span>
          </div>
          <div className="h-2 bg-secondary rounded-full overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-500"
              style={{ width: `${(completedMilestones / milestones.length) * 100}%` }}
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2">
          {progress.map((p) => (
            <TooltipProvider key={p.category}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="p-3 bg-secondary/50 rounded-lg cursor-pointer hover:bg-secondary transition-colors">
                    <p className="text-xs font-medium truncate">{p.category}</p>
                    <p className="text-lg font-semibold text-primary">
                      {p.completed}/{p.total}
                    </p>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <div className="space-y-1">
                    <p className="font-medium">{p.category}</p>
                    <p className="text-xs">Completed: {p.courses.slice(0, p.completed).join(', ') || 'None'}</p>
                    <p className="text-xs text-muted-foreground">
                      {p.remaining} more required
                    </p>
                  </div>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
