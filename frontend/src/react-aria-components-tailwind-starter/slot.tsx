// https://www.jacobparis.com/content/react-as-child
import React from 'react';

import { twMerge } from 'tailwind-merge';

export type AsChildProps<DefaultElementProps> =
  | ({ asChild?: false } & DefaultElementProps)
  | { asChild: true; children: React.ReactNode };

type cloneElement = React.ReactElement<{
  style?: React.CSSProperties;
  className?: string;
}>;

export function Slot({
  children,
  ...props
}: React.HTMLAttributes<HTMLElement> & {
  children?: React.ReactNode;
}) {
  if ('asChild' in props) {
    delete props.asChild;
  }

  if (React.isValidElement(children) && typeof children.props === 'object') {
    return React.cloneElement(children as cloneElement, {
      ...props,
      ...children.props,
      style: {
        ...props.style,
        ...(children as cloneElement).props?.style,
      },
      className: twMerge(
        props.className,
        (children as cloneElement).props?.className,
      ),
    });
  }

  if (React.Children.count(children) > 1) {
    React.Children.only(null);
  }
  return null;
}
