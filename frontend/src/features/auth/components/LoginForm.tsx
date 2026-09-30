import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Alert, Box, Button, Stack } from '@mui/material';
import { FormTextField } from '@/components';
import { ApiError } from '@/api';
import { loginInputSchema, type LoginInput } from '@/schemas';
import { useAuth } from '@/hooks';

export interface LoginFormProps {
  /** Called after a successful login (e.g. to navigate away). */
  onSuccess?: () => void;
}

const DEFAULT_VALUES: LoginInput = { email: '', password: '' };

/** Email/password login form (RHF + Zod). */
export function LoginForm({ onSuccess }: LoginFormProps): JSX.Element {
  const { login } = useAuth();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const {
    control,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<LoginInput>({
    resolver: zodResolver(loginInputSchema),
    defaultValues: DEFAULT_VALUES,
  });

  const onSubmit = handleSubmit(async (values) => {
    setSubmitError(null);
    try {
      await login(values);
      onSuccess?.();
    } catch (error) {
      setSubmitError(
        error instanceof ApiError
          ? error.message
          : 'Unable to sign in. Please check your credentials and try again.',
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
          autoComplete="current-password"
          required
        />
        <Button type="submit" variant="contained" size="large" disabled={isSubmitting}>
          {isSubmitting ? 'Signing in…' : 'Sign in'}
        </Button>
      </Stack>
    </Box>
  );
}
