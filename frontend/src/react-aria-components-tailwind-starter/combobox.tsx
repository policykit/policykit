import React from 'react';
import {
  ComboBox as RACComboBox,
  ComboBoxProps as RACComboBoxProps,
  ComboBoxStateContext,
  GroupProps,
  Group,
  composeRenderProps,
} from 'react-aria-components';
import { ButtonProps, Button } from './button';
import { inputField } from './utils';
import { twMerge } from 'tailwind-merge';
import {
  SelectListBox,
  SelectListItem,
  SelectListItemDescription,
  SelectListItemLabel,
  SelectPopover,
  SelectSection,
} from './select';
import { Input } from './field';
import { ChevronDownIcon } from './icons/outline/chevron-down';
import { XIcon } from './icons/outline/x';

export function ComboBox(props: RACComboBoxProps<object>) {
  return (
    <RACComboBox
      {...props}
      data-ui="comboBox"
      className={composeRenderProps(props.className, (className) =>
        twMerge(['w-full min-w-56', inputField, className]),
      )}
    />
  );
}

export function ComboBoxGroup(props: GroupProps) {
  return (
    <Group
      data-ui="control"
      {...props}
      className={composeRenderProps(props.className, (className) =>
        twMerge([
          'group/combobox',
          'isolate',
          'grid',
          'grid-cols-[36px_1fr_minmax(40px,max-content)_minmax(40px,max-content)]',
          'sm:grid-cols-[36px_1fr_minmax(36px,max-content)_minmax(36px,max-content)]',
          'items-center',

          // Icon
          'sm:[&>[data-ui=icon]:has(+input)]:size-4',
          '[&>[data-ui=icon]:has(+input)]:size-5',
          '[&>[data-ui=icon]:has(+input)]:row-start-1',
          '[&>[data-ui=icon]:has(+input)]:col-start-1',
          '[&>[data-ui=icon]:has(+input)]:place-self-center',
          '[&>[data-ui=icon]:has(+input)]:text-muted',
          '[&>[data-ui=icon]:has(+input)]:z-10',

          // Input
          '[&>input]:row-start-1',
          '[&>input]:col-span-full',
          '[&>input:not([class*=pe-])]:pe-10',
          'sm:[&>input:not([class*=pe-])]:pe-9',

          '[&>input:has(+[data-ui=clear]:not(:last-of-type))]:pe-20',
          'sm:[&>input:has(+[data-ui=clear]:not(:last-of-type))]:pe-16',

          '[&:has([data-ui=icon]+input)>input]:ps-10',
          'sm:[&:has([data-ui=icon]+input)>input]:ps-8',

          // Trigger button
          '*:data-[ui=trigger]:row-start-1',
          '*:data-[ui=trigger]:-col-end-1',
          '*:data-[ui=trigger]:place-self-center',

          // Clear button
          '*:data-[ui=clear]:row-start-1',
          '*:data-[ui=clear]:-col-end-2',
          '*:data-[ui=clear]:justify-self-end',
          '[&>[data-ui=clear]:last-of-type]:-col-end-1',
          '[&>[data-ui=clear]:last-of-type]:place-self-center',

          className,
        ]),
      )}
    />
  );
}

export const ComboBoxInput = Input;

export function ComboBoxButton({
  triggerIcon = <ChevronDownIcon />,
}: {
  triggerIcon?: React.ReactNode;
}) {
  return (
    <Button
      isIconOnly
      size="sm"
      data-ui="trigger"
      variant="plain"
      className="text-muted/50 group-hover/combobox:text-foreground"
    >
      {triggerIcon}
    </Button>
  );
}

export function ComboBoxClearButton({
  onPress,
  ...props
}: Omit<ButtonProps, 'tooltip' | 'slot' | 'variant' | 'size' | 'isIconOnly'>) {
  const state = React.useContext(ComboBoxStateContext);

  return (
    <Button
      {...props}
      className={composeRenderProps(props.className, (className) => {
        return twMerge(
          '[&:not(:hover)]:text-muted',
          'not-last:-me-1',
          state?.inputValue
            ? 'visible focus-visible:-outline-offset-2'
            : 'invisible',
          className,
        );
      })}
      slot={null}
      data-ui="clear"
      size="sm"
      isIconOnly
      variant="plain"
      onPress={(e) => {
        state?.setSelectedKey(null);
        onPress?.(e);
      }}
    >
      <XIcon
        aria-label="Clear"
        className="size-4 sm:size-[calc(--spacing(4)-1px)]"
      />
    </Button>
  );
}

export const ComboBoxPopover = SelectPopover;

export const ComboBoxSection = SelectSection;

export const ComboBoxListBox = SelectListBox;

export const ComboBoxListItem = SelectListItem;

export const ComboBoxListItemLabel = SelectListItemLabel;

export const ComboBoxListItemDescription = SelectListItemDescription;
