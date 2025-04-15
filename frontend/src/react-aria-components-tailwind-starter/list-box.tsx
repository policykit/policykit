import React from 'react';
import {
  ListBox as RACListBox,
  ListBoxItem as RACListBoxItem,
  ListBoxProps as RACListBoxProps,
  ListBoxItemProps,
  composeRenderProps,
} from 'react-aria-components';
import { composeTailwindRenderProps } from './utils';
import { twMerge } from 'tailwind-merge';

export interface ListBoxProps<T>
  extends Omit<RACListBoxProps<T>, 'layout' | 'orientation'> {}

export const ListBox = React.forwardRef(
  <T extends object>(
    props: ListBoxProps<T>,
    ref: React.Ref<HTMLDivElement>,
  ) => {
    return (
      <RACListBox
        {...props}
        ref={ref}
        className={composeTailwindRenderProps(props.className, [
          'outline-hidden',
        ])}
      />
    );
  },
) as <T extends object>(
  props: ListBoxProps<T> & { ref?: React.Ref<HTMLDivElement> },
) => React.JSX.Element;

export const ListBoxItem = React.forwardRef(
  (props: ListBoxItemProps, ref: React.Ref<HTMLLIElement>) => {
    const textValue =
      props.textValue ||
      (typeof props.children === 'string' ? props.children : undefined);

    return (
      <RACListBoxItem
        {...props}
        ref={ref}
        textValue={textValue}
        className={composeRenderProps(
          props.className,
          (className, { isFocusVisible, isDisabled }) =>
            twMerge(
              'group relative flex outline-0',
              isDisabled && 'opacity-50',
              isFocusVisible &&
                'outline-ring outline outline-2 outline-offset-2',
              className,
            ),
        )}
      />
    );
  },
) as (
  props: ListBoxItemProps & { ref?: React.Ref<HTMLLIElement> },
) => React.JSX.Element;

