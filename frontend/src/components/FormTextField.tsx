import { Controller, type Control, type FieldValues, type Path } from 'react-hook-form';
import { TextField, type TextFieldProps } from '@mui/material';

export type FormTextFieldProps<TFieldValues extends FieldValues> = {
  name: Path<TFieldValues>;
  control: Control<TFieldValues>;
  label: string;
} & Omit<TextFieldProps, 'name' | 'error' | 'helperText' | 'defaultValue'>;

/**
 * React Hook Form-bound MUI TextField. Surfaces validation errors via
 * `helperText` and links them to the input with `aria-describedby`, so form
 * errors are announced and associated with their field.
 */
export function FormTextField<TFieldValues extends FieldValues>({
  name,
  control,
  label,
  ...textFieldProps
}: FormTextFieldProps<TFieldValues>): JSX.Element {
  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState }) => {
        const hasError = Boolean(fieldState.error);
        const helperId = hasError ? `${name}-error` : undefined;
        const helperText = fieldState.error?.message;
        return (
          <TextField
            {...textFieldProps}
            {...field}
            id={textFieldProps.id ?? name}
            value={field.value ?? ''}
            label={label}
            error={hasError}
            fullWidth={textFieldProps.fullWidth ?? true}
            inputProps={{
              ...textFieldProps.inputProps,
              ...(helperId ? { 'aria-describedby': helperId } : {}),
            }}
            {...(helperText !== undefined ? { helperText } : {})}
            {...(helperId ? { FormHelperTextProps: { id: helperId } } : {})}
          />
        );
      }}
    />
  );
}
