import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useForm, Controller, type Control } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  Alert,
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
  MenuItem,
  Radio,
  Stack,
  Step,
  StepLabel,
  Stepper,
  TextField,
  Typography,
} from '@mui/material';
import { ApiError } from '@/api';
import { FormTextField, LoadingState, ErrorState, DisclaimerBanner } from '@/components';
import { RoofMap } from '@/features/map';
import { useProjects } from '@/features/projects';
import { useCreateAnalysis, useSubmitAnalysis } from '@/features/analyses';
import { buildPath } from '@/routes/paths';
import { wizardFormSchema, type WizardFormValues } from './formSchema';
import { useImagerySources } from './hooks';
import { SAMPLE_AREA, SAMPLE_AREA_BBOX, SAMPLE_AREA_FEATURE_COLLECTION, SAMPLE_AREA_LABEL } from './sampleArea';

const STEP_LABELS = ['Project', 'Select area', 'Imagery source', 'Name & review'] as const;
const STEP_FIELDS: Array<Array<keyof WizardFormValues>> = [
  ['project'],
  [],
  ['imagerySource'],
  ['name'],
];

interface ProjectSelectProps {
  control: Control<WizardFormValues>;
  projects: { id: string; name: string }[];
}

function ProjectSelect({ control, projects }: ProjectSelectProps): JSX.Element {
  return (
    <Controller
      name="project"
      control={control}
      render={({ field, fieldState }) => (
        <TextField
          {...field}
          select
          fullWidth
          label="Project"
          required
          error={Boolean(fieldState.error)}
          helperText={fieldState.error?.message}
        >
          {projects.map((project) => (
            <MenuItem key={project.id} value={project.id}>
              {project.name}
            </MenuItem>
          ))}
        </TextField>
      )}
    />
  );
}

export interface AnalysisWizardProps {
  /** Optional pre-selected project id (overrides the `?project=` query param). */
  projectId?: string;
}

/**
 * Multi-step wizard for the sample-path analysis journey:
 *   1. pick/confirm a project, 2. confirm the bundled sample area (read-only
 *   map), 3. pick an imagery source (bundled sample preselected), 4. name +
 *   review + submit. On submit it creates the draft analysis then submits it
 *   (with a generated Idempotency-Key) and routes to the processing screen.
 */
export function AnalysisWizard({ projectId }: AnalysisWizardProps): JSX.Element {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const preselectedProject = projectId ?? searchParams.get('project') ?? '';

  const [activeStep, setActiveStep] = useState(0);
  const [globalError, setGlobalError] = useState<string | null>(null);

  const projectsQuery = useProjects({ ordering: '-created_at' });
  const sourcesQuery = useImagerySources();
  const createAnalysis = useCreateAnalysis();
  const submitAnalysis = useSubmitAnalysis();

  const { control, handleSubmit, trigger, setValue, setError, watch } = useForm<WizardFormValues>({
    resolver: zodResolver(wizardFormSchema),
    defaultValues: { project: preselectedProject, imagerySource: '', name: 'Sample rooftop analysis' },
  });

  const selectedSource = watch('imagerySource');

  // Preselect a project once the list loads (if none chosen yet).
  useEffect(() => {
    if (watch('project')) return;
    const projects = projectsQuery.data?.results ?? [];
    const preferred = projects.find((project) => project.id === preselectedProject) ?? projects[0];
    if (preferred) setValue('project', preferred.id);
  }, [projectsQuery.data, preselectedProject, setValue, watch]);

  // Preselect the bundled sample imagery source (uploaded_raster) once loaded.
  useEffect(() => {
    if (selectedSource) return;
    const sources = sourcesQuery.data ?? [];
    const preferred = sources.find((source) => source.name === 'uploaded_raster') ?? sources[0];
    if (preferred) setValue('imagerySource', preferred.name);
  }, [sourcesQuery.data, selectedSource, setValue]);

  const isSubmitting = createAnalysis.isPending || submitAnalysis.isPending;

  const handleNext = async (): Promise<void> => {
    const valid = await trigger(STEP_FIELDS[activeStep]);
    if (valid) setActiveStep((step) => Math.min(step + 1, STEP_LABELS.length - 1));
  };

  const handleBack = (): void => setActiveStep((step) => Math.max(step - 1, 0));

  const onSubmit = handleSubmit(async (values) => {
    setGlobalError(null);
    try {
      const analysis = await createAnalysis.mutateAsync({
        projectId: values.project,
        name: values.name,
        area: SAMPLE_AREA,
      });
      await submitAnalysis.mutateAsync(analysis.id);
      navigate(buildPath.analysisProcessing(analysis.id));
    } catch (error) {
      if (error instanceof ApiError) {
        const fieldErrors = error.fieldErrors;
        if (fieldErrors?.name) setError('name', { message: fieldErrors.name });
        setGlobalError(error.message);
      } else {
        setGlobalError('Something went wrong submitting the analysis. Please try again.');
      }
    }
  });

  return (
    <Box>
      <Stepper activeStep={activeStep} sx={{ mb: 4 }} alternativeLabel>
        {STEP_LABELS.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      <form onSubmit={onSubmit} noValidate>
        {activeStep === 0 && (
          <Stack spacing={2}>
            <Typography variant="h4" component="h2">
              Choose a project
            </Typography>
            {projectsQuery.isPending && <LoadingState label="Loading projects…" />}
            {projectsQuery.isError && (
              <ErrorState
                message={projectsQuery.error.message}
                onRetry={() => void projectsQuery.refetch()}
              />
            )}
            {projectsQuery.isSuccess && projectsQuery.data.results.length === 0 && (
              <Alert severity="info">
                You have no projects yet. Create a project from the dashboard first.
              </Alert>
            )}
            {projectsQuery.isSuccess && projectsQuery.data.results.length > 0 && (
              <ProjectSelect control={control} projects={projectsQuery.data.results} />
            )}
          </Stack>
        )}

        {activeStep === 1 && (
          <Stack spacing={2}>
            <Typography variant="h4" component="h2">
              Select area
            </Typography>
            <Alert severity="info">
              Using the bundled sample area ({SAMPLE_AREA_LABEL}). No drawing or upload is required
              for the sample path.
            </Alert>
            <Box sx={{ height: 360 }}>
              <RoofMap
                features={SAMPLE_AREA_FEATURE_COLLECTION}
                bounds={SAMPLE_AREA_BBOX}
                ariaLabel="Bundled sample analysis area"
              />
            </Box>
          </Stack>
        )}

        {activeStep === 2 && (
          <Stack spacing={2}>
            <Typography variant="h4" component="h2">
              Select imagery source
            </Typography>
            {sourcesQuery.isPending && <LoadingState label="Loading imagery sources…" />}
            {sourcesQuery.isError && (
              <ErrorState
                message={sourcesQuery.error.message}
                onRetry={() => void sourcesQuery.refetch()}
              />
            )}
            {sourcesQuery.isSuccess && (
              <Controller
                name="imagerySource"
                control={control}
                render={({ field, fieldState }) => (
                  <Box>
                    <Stack
                      component="ul"
                      role="radiogroup"
                      aria-label="Imagery source"
                      spacing={1.5}
                      sx={{ listStyle: 'none', p: 0, m: 0 }}
                    >
                      {sourcesQuery.data.map((source) => {
                        const checked = field.value === source.name;
                        return (
                          <Box component="li" key={source.name}>
                            <Card variant="outlined" sx={{ borderColor: checked ? 'primary.main' : undefined }}>
                              <CardActionArea onClick={() => field.onChange(source.name)}>
                                <CardContent>
                                  <Stack direction="row" spacing={1.5} alignItems="flex-start">
                                    <Radio
                                      checked={checked}
                                      tabIndex={-1}
                                      inputProps={{ 'aria-label': source.title }}
                                    />
                                    <Box>
                                      <Typography variant="subtitle1">
                                        {source.title}
                                        {source.name === 'uploaded_raster' ? ' (bundled sample)' : ''}
                                      </Typography>
                                      <Typography variant="body2" color="text.secondary">
                                        {source.description}
                                      </Typography>
                                    </Box>
                                  </Stack>
                                </CardContent>
                              </CardActionArea>
                            </Card>
                          </Box>
                        );
                      })}
                    </Stack>
                    {fieldState.error && (
                      <Typography variant="caption" color="error" sx={{ mt: 1, display: 'block' }}>
                        {fieldState.error.message}
                      </Typography>
                    )}
                  </Box>
                )}
              />
            )}
          </Stack>
        )}

        {activeStep === 3 && (
          <Stack spacing={2}>
            <Typography variant="h4" component="h2">
              Name & review
            </Typography>
            <FormTextField name="name" control={control} label="Analysis name" required autoFocus />
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>
                  Review
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Area: {SAMPLE_AREA_LABEL} (bundled sample)
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Imagery source: {selectedSource || 'bundled sample'}
                </Typography>
              </CardContent>
            </Card>
            {globalError && <Alert severity="error">{globalError}</Alert>}
            <DisclaimerBanner variant="banner" />
          </Stack>
        )}

        <Stack direction="row" spacing={1.5} sx={{ mt: 3 }} justifyContent="space-between">
          <Button onClick={handleBack} disabled={activeStep === 0 || isSubmitting}>
            Back
          </Button>
          {activeStep < STEP_LABELS.length - 1 ? (
            <Button variant="contained" onClick={() => void handleNext()}>
              Next
            </Button>
          ) : (
            <Button type="submit" variant="contained" disabled={isSubmitting}>
              {isSubmitting ? 'Submitting…' : 'Submit analysis'}
            </Button>
          )}
        </Stack>
      </form>
    </Box>
  );
}
