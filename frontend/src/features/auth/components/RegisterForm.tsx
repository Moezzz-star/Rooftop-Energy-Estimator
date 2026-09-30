import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Alert, Box, Button, Stack } from '@mui/material';
import { FormTextField } from '@/components';
import { ApiError } from '@/api';
import { registerInputSchema, type RegisterInput } from '@/schemas';
import { useAuth } from '@/hooks';

export interface RegisterFormProps {
  onSuccess?: () => void;
}

const DEFAULT_VALUES: RegisterInput = { email: '', password: '', confirmPassword: '' };

/** Account registration form (RHF + Zod, with password confirmation). */
export function RegisterForm({ onSuccess }: RegisterFormProps): JSX.Element {
  const { register } = useAuth();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const {
    control,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<RegisterInput>({
    resolver: zodResolver(registerInputSchema),
    defaultValues: DEFAULT_VALUES,
  });

  const onSubmit = handleSubmit(async (values) => {
    setSubmitError(null);
    try {
      await register(values);
      onSuccess?.();
    } catch (error) {
      setSubmitError(
        error instanceof ApiError
          ? error.message
          : 'Unable to create your account. Please try again.',
      );
    }
  });

  return (
    <Box component="form" onSubmit={onSubmit} noValidate>
      <Stack spacing={2}>
        {submitError && <Alert severity="error">{submitError}</Alert>}
        <FormTextField
          name="email"
          control={control}
          label="Email"
          type="email"
          autoComplete="email"
          required
        />
        <FormTextField
          name="password"
          control={control}
          label="Password"
          type="password"
          autoComplete="new-password"
          required
        />
        <FormTextField
          name="confirmPassword"
          control={control}
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          required
        />
        <Button type="submit" variant="contained" size="large" disabled={isSubmitting}>
          {isSubmitting ? 'Creating account…' : 'Create account'}
        </Button>
      </Stack>
    </Box>
  );
}
