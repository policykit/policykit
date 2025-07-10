import React from 'react';
import { twMerge } from 'tailwind-merge';
import {
  composeRenderProps,
  Group,
  GroupProps,
  Switch as RACSwitch,
  SwitchProps as RACSwitchProps,
  SwitchRenderProps,
} from 'react-aria-components';
import { groupBox, composeTailwindRenderProps } from './utils';
import { DescriptionProvider, DescriptionContext, LabeledGroup } from './field';

export function SwitchGroup(props: GroupProps) {
  return (
    <LabeledGroup>
      <Group
        {...props}
        className={composeTailwindRenderProps(props.className, groupBox)}
      ></Group>
    </LabeledGroup>
  );
}

export function Switches({
  className,
  ...props
}: React.JSX.IntrinsicElements['div']) {
  return (
    <div
      {...props}
      data-ui="box"
      className={twMerge(
        'flex flex-col',
        // When any switch item has description, apply all `font-medium` to all switch item labels
        'has-data-[ui=description]:[&_label]:font-medium',
        className,
      )}
    />
  );
}

export function SwitchField({
  className,
  ...props
}: React.JSX.IntrinsicElements['div']) {
  return (
    <DescriptionProvider>
      <div
        {...props}
        data-ui="field"
        className={twMerge(
          'group flex flex-col gap-y-1',
          'has-[label[data-label-placement=start]]:[&_[data-ui=description]:not([class*=pe-])]:pe-[calc(theme(width.8)+16px)]',
          'has-[label[data-label-placement=end]]:[&_[data-ui=description]:not([class*=ps-])]:ps-[calc(theme(width.8)+12px)]',
          'has-data-[ui=description]:[&_label]:font-medium',
          'has-[label[data-disabled]]:**:data-[ui=description]:opacity-50',
          className,
        )}
      />
    </DescriptionProvider>
  );
}

interface SwitchProps extends RACSwitchProps {
  labelPlacement?: 'start' | 'end';
  size?: 'lg';
  render?: never;
}

export interface CustomRenderSwitchProps
  extends Omit<RACSwitchProps, 'children'> {
  render: React.ReactElement | ((props: SwitchRenderProps) => React.ReactNode);
  children?: never;
  size?: never;
  labelPlacement?: never;
}

export function Switch(props: SwitchProps | CustomRenderSwitchProps) {
  const descriptionContext = React.useContext(DescriptionContext);

  if (props.render) {
    const { render, ...restProps } = props;

    return (
      <RACSwitch
        {...restProps}
        aria-describedby={descriptionContext?.['aria-describedby']}
        className={composeRenderProps(
          props.className,
          (className, { isDisabled }) =>
            twMerge(
              'group text-base/6 sm:text-sm/6',
              isDisabled && 'opacity-50',
              className,
            ),
        )}
      >
        {render}
      </RACSwitch>
    );
  }

  const { labelPlacement = 'end', size, children, ...restProps } = props;

  return (
    <RACSwitch
      {...restProps}
      aria-describedby={descriptionContext?.['aria-describedby']}
      data-label-placement={labelPlacement}
      className={composeRenderProps(
        props.className,
        (className, { isDisabled }) =>
          twMerge(
            'group flex items-center text-base/6 sm:text-sm/6',
            labelPlacement === 'start' && 'flex-row-reverse justify-between',
            isDisabled && 'opacity-50',
            className,
          ),
      )}
    >
      {(renderProps) => (
        <>
          <div
            className={twMerge(
              'flex h-6 w-11 shrink-0 cursor-default items-center rounded-full bg-zinc-200 p-0.5 dark:bg-zinc-800 ',
              size !== 'lg' && 'sm:h-5 sm:w-8',
              labelPlacement === 'end' ? 'me-3' : 'ms-3',
              renderProps.isReadOnly && 'opacity-50',
              renderProps.isSelected &&
                'bg-accent dark:bg-accent',
              renderProps.isDisabled && 'bg-gray-200 dark:bg-zinc-700',
              renderProps.isFocusVisible &&
                'outline-ring outline outline-2 outline-offset-2',
            )}
          >
            <span
              data-ui="handle"
              className={twMerge(
                'size-5',
                size !== 'lg' && 'sm:size-4',
                'rounded-full bg-white shadow transition-all ease-in-out',
                renderProps.isSelected && [
                  'translate-x-5 bg-[lch(from_var(--color-accent)_calc((49.44_-_l)_*_infinity)_0_0)] rtl:-translate-x-5',
                  size !== 'lg' && 'sm:translate-x-3 sm:rtl:-translate-x-3',
                ],
              )}
            />
          </div>
          {typeof children === 'function' ? children(renderProps) : children}
        </>
      )}
    </RACSwitch>
  );
}
