import React from 'react';
import {
  Button,
  ButtonProps,
  composeRenderProps,
  DisclosureGroupProps,
  DisclosurePanelProps,
  DisclosureGroup as RACDisclosureGroup,
  DisclosurePanel as RACDisclosurePanel,
} from 'react-aria-components';
import { twMerge } from 'tailwind-merge';
import { Text } from './text';

export { Disclosure } from 'react-aria-components';

export function DisclosureGroup(props: DisclosureGroupProps) {
  return (
    <RACDisclosureGroup
      {...props}
      className={composeRenderProps(props.className, (className) => {
        return twMerge([
          'flex flex-col [&>div:has(>button[aria-expanded]):not([class*=pb-]):not(:last-child)]:pb-4 [&>div:has(>button[aria-expanded]):not([class*=pt-]):not(:first-of-type)]:pt-4',
          className,
        ]);
      })}
    />
  );
}

export function DisclosurePanel({ children, ...props }: DisclosurePanelProps) {
  return (
    <RACDisclosurePanel {...props}>
      {React.Children.toArray(children).every(
        (child) => typeof child === 'string',
      ) ? (
        <Text>{children}</Text>
      ) : (
        children
      )}
    </RACDisclosurePanel>
  );
}

export function DisclosureControl(props: ButtonProps) {
  return (
    <Button
      {...props}
      slot="trigger"
      className={composeRenderProps(
        props.className,
        (className, { isFocusVisible }) => {
          return twMerge([
            'group [&_svg[data-ui=icon]:not(:hover)]:text-muted mb-2 flex items-center gap-x-2 rounded-sm outline-hidden [&_svg[data-ui=icon]:not([class*=size-])]:size-5',
            isFocusVisible && [
              'outline',
              'outline-2',
              'outline-ring',
              'outline-offset-2',
            ],
            className,
          ]);
        },
      )}
    />
  );
}
