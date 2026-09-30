import type { ReactElement } from 'react';
import { ROUTES } from './paths';
import { ProjectDetailPage } from '@/pages/ProjectDetailPage';
import { NewAnalysisPage } from '@/pages/NewAnalysisPage';
import { ProcessingPage } from '@/pages/ProcessingPage';
import { ResultsPage } from '@/pages/ResultsPage';

export interface FeatureRoute {
  /** Route path (relative or absolute, matched under the protected shell). */
  path: string;
  element: ReactElement;
}

/**
 * SEAM for the wizard/processing/results engineer.
 *
 * These protected feature routes are rendered by `AppRouter` inside the
 * authenticated `AppShell`. To build out the wizard/processing/results, either:
 *   1. Replace the BODY of the referenced page components (ProjectDetailPage,
 *      NewAnalysisPage, ProcessingPage, ResultsPage) — keep their export names
 *      and route params; OR
 *   2. Add new entries to this array for additional screens.
 *
 * You should NOT need to edit `AppRouter.tsx` or `ProtectedRoute.tsx`.
 */
export const featureRoutes: FeatureRoute[] = [
  { path: ROUTES.projectDetail, element: <ProjectDetailPage /> },
  { path: ROUTES.newAnalysis, element: <NewAnalysisPage /> },
  { path: ROUTES.analysisProcessing, element: <ProcessingPage /> },
  { path: ROUTES.analysisResults, element: <ResultsPage /> },
];
