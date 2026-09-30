/**
 * Central route path constants. Import these everywhere instead of hardcoding
 * URL strings. The wizard/processing/results engineer should add any new paths
 * here and register screens in `featureRoutes` (see featureRoutes.tsx) rather
 * than editing the router core (AppRouter.tsx).
 */
export const ROUTES = {
  login: '/login',
  register: '/register',
  dashboard: '/dashboard',
  projectDetail: '/projects/:projectId',
  newAnalysis: '/analyses/new',
  analysisProcessing: '/analyses/:analysisId/processing',
  analysisResults: '/analyses/:analysisId/results',
} as const;

/** Path builders for parameterized routes (keeps `:param` usage type-safe). */
export const buildPath = {
  projectDetail: (projectId: string): string => `/projects/${projectId}`,
  analysisProcessing: (analysisId: string): string => `/analyses/${analysisId}/processing`,
  analysisResults: (analysisId: string): string => `/analyses/${analysisId}/results`,
} as const;
