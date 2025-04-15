import {
  TimeField as RACTimeField,
  TimeFieldProps as RACTimeFieldProps,
  TimeValue,
  composeRenderProps,
} from 'react-aria-components';
import { twMerge } from 'tailwind-merge';
import { inputField } from './utils';

export interface TimeFieldProps<T extends TimeValue>
  extends RACTimeFieldProps<T> {}

export function TimeField<T extends TimeValue>(props: RACTimeFieldProps<T>) {
  return (
    <RACTimeField
      {...props}
      className={composeRenderProps(
        props.className,
        (className, { isDisabled }) => {
          return twMerge(
            inputField,
            'items-start',
            // RAC does not set disable to time field when it is disable
            // So we have to style disable state for none input
            isDisabled && '[&>:not(input)]:opacity-50',
            className,
          );
        },
      )}
    />
  );
}
