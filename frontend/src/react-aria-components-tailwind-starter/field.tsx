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
  hint,
  displayLevel = 3,
  children,
  ...props
}: LabelProps & {
  requiredHint?: boolean;
  hint?: 'required' | 'optional';
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
        hint === 'required' &&
          "after:ms-0.5 after:text-red-600 after:content-['*']",
        props.className,
      )}
    >
      {children}
      {hint === 'optional' && (
        <span className="text-muted ps-0.5 font-normal ms-auto">Optional</span>
      )}
    </RACLabel>
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
        twMerge('block text-base/6 text-red-600 sm:text-sm/6', className),
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
          (className, renderProps) => {
            return twMerge(
              'border-input w-full rounded-md border shadow-xs outline-hidden',
              'px-3 py-[calc(--spacing(2.5)-1px)] sm:py-[calc(--spacing(1.5)-1px)]',
              'placeholder:text-muted text-base/6 sm:text-sm/6',
              'dark:shadow-none [&[readonly]]:bg-zinc-800/5 dark:[&[readonly]]:bg-white/10',
              renderProps.isDisabled && 'opacity-50',
              renderProps.isInvalid && 'border-red-600',
              renderProps.isFocused
                ? 'border-ring ring-ring ring-1'
                : '[&[readonly]]:border-transparent',
              className,
            );
          },
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
          'border-input w-full rounded-md border px-3 py-1 shadow-xs outline-hidden',
          'placeholder:text-muted text-base/6 sm:text-sm/6',
          '[&[readonly]]:bg-zinc-800/5 dark:[&[readonly]]:bg-white/10',
          renderProps.isDisabled && 'opacity-50',
          renderProps.isInvalid && 'border-red-600',
          renderProps.isFocused
            ? 'border-ring ring-ring ring-1'
            : '[&[readonly]]:border-transparent',
          className,
        ),
      )}
    />
  );
}
