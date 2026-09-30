import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
} from '@mui/material';
import { FormTextField } from '@/components';
import { createProjectInputSchema, type CreateProjectInput, type Project } from '@/schemas';
import { useCreateProject } from '../hooks';

export interface CreateProjectDialogProps {
  open: boolean;
  onClose: () => void;
  /** Called after a project is created successfully. */
  onCreated?: (project: Project) => void;
}

const DEFAULT_VALUES: CreateProjectInput = { name: '', description: '' };

/** Modal form (RHF + Zod) for creating a project. */
export function CreateProjectDialog({
  open,
  onClose,
  onCreated,
}: CreateProjectDialogProps): JSX.Element {
  const { control, handleSubmit, reset } = useForm<CreateProjectInput>({
    resolver: zodResolver(createProjectInputSchema),
    defaultValues: DEFAULT_VALUES,
  });
  const createProject = useCreateProject();

  const handleClose = (): void => {
    reset(DEFAULT_VALUES);
    createProject.reset();
    onClose();
  };

  const onSubmit = handleSubmit((values) => {
    createProject.mutate(values, {
      onSuccess: (project) => {
        reset(DEFAULT_VALUES);
        onCreated?.(project);
        onClose();
      },
    });
  });

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="sm" aria-labelledby="create-project-title">
      <form onSubmit={onSubmit} noValidate>
        <DialogTitle id="create-project-title">New project</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {createProject.isError && (
              <Alert severity="error">{createProject.error.message}</Alert>
            )}
            <FormTextField
              name="name"
              control={control}
              label="Project name"
              required
              autoFocus
            />
            <FormTextField
              name="description"
              control={control}
              label="Description"
              multiline
              minRows={3}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose} disabled={createProject.isPending}>
            Cancel
          </Button>
          <Button type="submit" variant="contained" disabled={createProject.isPending}>
            {createProject.isPending ? 'Creating…' : 'Create project'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
