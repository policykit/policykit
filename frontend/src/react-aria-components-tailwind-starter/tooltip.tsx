import React from 'react';
import {
  Tooltip as RACTooltip,
  TooltipProps as RACTooltipProps,
} from 'react-aria-components';
import { composeTailwindRenderProps } from './utils';
import { FocusableOptions, mergeProps, useFocusable } from 'react-aria';

export { TooltipTrigger } from 'react-aria-components';

export interface TooltipProps extends Omit<RACTooltipProps, 'children'> {
  children: React.ReactNode;
}

export function Tooltip({ children, ...props }: TooltipProps) {
  return (
    <RACTooltip
      {...props}
      offset={6}
      className={composeTailwindRenderProps(props.className, [
        'group max-w-64 rounded-md px-3 py-1.5',
        'text-wrap text-pretty',
        'shadow-2xs dark:border dark:shadow-none',
        React.Children.toArray(children).every(
          (child) => typeof child === 'string',
        )
          ? 'bg-zinc-950 text-xs text-white dark:bg-zinc-800'
          : 'border bg-background',
      ])}
    >
      {children}
    </RACTooltip>
  );
}

// https://argos-ci.com/blog/react-aria-migration
export function NonFousableTooltipTarget(props: {
  children: React.ReactElement;
}) {
  const triggerRef = React.useRef(null);
  const { focusableProps } = useFocusable(props.children.props as FocusableOptions, triggerRef);

  return React.cloneElement(
    props.children,
    mergeProps(focusableProps, { tabIndex: 0 }, props.children.props as React.HTMLProps<HTMLElement>, {
      ref: triggerRef,
    }),
  );
}

export function NativeTooltip({
  title,
  ...props
}: React.JSX.IntrinsicElements['div'] & { title: string }) {
  return <div title={title} role="presentation" {...props} />;
}
