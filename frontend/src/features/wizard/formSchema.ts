import { z } from 'zod';

/** Validation for the sample-path analysis wizard inputs. */
export const wizardFormSchema = z.object({
  project: z.string().uuid('Select a project'),
  imagerySource: z.string().min(1, 'Select an imagery source'),
  name: z
    .string()
    .min(1, 'Analysis name is required')
    .max(120, 'Analysis name must be 120 characters or fewer'),
});

export type WizardFormValues = z.infer<typeof wizardFormSchema>;
