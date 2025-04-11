import React from 'react';
import {
  FieldErrorProps,
  InputProps,
  LabelProps,
  FieldError as RACFieldError,
  Input as RACInput,
  Label as RACLabel,
  TextProps,
  LabelContext,
  GroupContext,
  TextFieldProps as RACTextFieldProps,
  TextField as RACTextField,
  TextArea as RACTextArea,
  TextAreaProps as RACTextAreaProps,
  Text as RACText,
  composeRenderProps,
} from 'react-aria-components';
import { twMerge } from 'tailwind-merge';
import { DisplayLevel, displayLevels, inputField } from './utils';
import { Text } from './text';

// https://react-spectrum.adobe.com/react-aria/Group.html#advanced-customization
export function LabeledGroup({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  const labelId = React.useId();

  return (
    <LabelContext.Provider value={{ id: labelId, elementType: 'span' }}>
      <GroupContext.Provider value={{ 'aria-labelledby': labelId }}>
        <div
          className={twMerge(
            ['[&>[data-ui=label]:first-of-type:not([class*=mb])]:mb-2'],
            className,
          )}
        >
          {children}
        </div>
      </GroupContext.Provider>
    </LabelContext.Provider>
  );
}

export function Label({
  requiredHint,
  displayLevel = 3,
  ...props
}: LabelProps & {
  requiredHint?: boolean;
  displayLevel?: DisplayLevel;
}) {
  return (
    <RACLabel
      {...props}
      data-ui="label"
      className={twMerge(
        'inline-block min-w-max text-pretty',
        'group-disabled:opacity-50',
        displayLevels[displayLevel],
        requiredHint &&
          "after:text-destructive after:ms-0.5 after:content-['*']",
        props.className,
      )}
    />
  );
}

export const DescriptionContext = React.createContext<{
  'aria-describedby'?: string;
} | null>(null);

export function DescriptionProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const descriptionId: string | null = React.useId();
  const [descriptionRendered, setDescriptionRendered] = React.useState(true);

  React.useLayoutEffect(() => {
    if (!document.getElementById(descriptionId)) {
      setDescriptionRendered(false);
    }
  }, [descriptionId]);

  return (
    <DescriptionContext.Provider
      value={{
        'aria-describedby': descriptionRendered ? descriptionId : undefined,
      }}
    >
      {children}
    </DescriptionContext.Provider>
  );
}

/**
 * RAC will auto associate <RACText slot="description"/> with TextField/NumberField/RadioGroup/CheckboxGroup/DatePicker etc,
 * but not for Switch/Checkbox/Radio and our custom components. We use follow pattern to associate description for
 * Switch/Checkbox/Radio https://react-spectrum.adobe.com/react-aria/Switch.html#advanced-customization
 */
export function Description({ className, ...props }: TextProps) {
  const describedby =
    React.useContext(DescriptionContext)?.['aria-describedby'];

  return describedby ? (
    <Text
      {...props}
      id={describedby}
      data-ui="description"
      className={twMerge('block group-disabled:opacity-50', className)}
    />
  ) : (
    <RACText
      {...props}
      data-ui="description"
      slot="description"
      className={twMerge(
        'text-muted block text-base/6 text-pretty sm:text-sm/6',
        'group-disabled:opacity-50',
        className,
      )}
    />
  );
}

export function TextField(props: RACTextFieldProps) {
  return (
    <RACTextField
      {...props}
      data-ui="text-field"
      className={composeRenderProps(props.className, (className) =>
        twMerge(inputField, className),
      )}
    />
  );
}

export function FieldError(props: FieldErrorProps) {
  return (
    <RACFieldError
      {...props}
      data-ui="errorMessage"
      className={composeRenderProps(props.className, (className) =>
        twMerge('text-destructive block text-base/6 sm:text-sm/6', className),
      )}
    />
  );
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  function Input(props, ref) {
    return (
      <RACInput
        {...props}
        ref={ref}
        className={composeRenderProps(
          props.className,
          (className, renderProps) =>
            twMerge(
              'border-input w-full rounded-md border outline-hidden',
              'px-3 py-[calc(--spacing(2.5)-1px)] sm:py-[calc(--spacing(1.5)-1px)]',
              'placeholder:text-muted text-base/6 sm:text-sm/6',
              '[&[readonly]]:bg-zinc-50',
              'dark:[&[readonly]]:bg-white/10',
              renderProps.isDisabled && 'opacity-50',
              renderProps.isInvalid && 'border-destructive',
              renderProps.isFocused && 'border-ring ring-ring ring-1',
              className,
            ),
        )}
      />
    );
  },
);

export function TextArea(props: RACTextAreaProps) {
  return (
    <RACTextArea
      {...props}
      className={composeRenderProps(props.className, (className, renderProps) =>
        twMerge(
          'border-input w-full rounded-md border px-3 py-1 outline-hidden',
          'placeholder:text-muted text-base/6 sm:text-sm/6',
          '[&[readonly]]:bg-zinc-50',
          'dark:[&[readonly]]:bg-white/10',
          renderProps.isDisabled && 'opacity-50',
          renderProps.isInvalid && 'border-destructive',
          renderProps.isFocused && 'border-ring ring-ring ring-1',
          className,
        ),
      )}
    />
  );
}
