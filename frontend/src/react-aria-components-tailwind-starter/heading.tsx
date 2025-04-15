import React from 'react';
import {
  Heading as RACHeading,
  HeadingProps as RACHeadingProps,
} from 'react-aria-components';
import { twMerge } from 'tailwind-merge';
import { DisplayLevel, displayLevels } from './utils';

export type BaseHeadingProps = {
  level?: DisplayLevel;
  elementType?: never;
} & RACHeadingProps;

type CustomElement = {
  level?: never;
  elementType: 'div';
} & React.JSX.IntrinsicElements['div'];

export type HeadingProps = {
  displayLevel?: DisplayLevel;
} & (BaseHeadingProps | CustomElement);

export const Heading = React.forwardRef<
  HTMLHeadingElement | HTMLDivElement,
  HeadingProps
>(function Heading({ elementType, ...props }, ref) {
  if (elementType) {
    const { displayLevel = 1, className, ...restProps } = props;
    return (
      <div
        {...restProps}
        ref={ref}
        className={twMerge(displayLevels[displayLevel], className)}
      />
    );
  }

  const { level = 1, displayLevel, className, ...restProps } = props;

  return (
    <RACHeading
      {...restProps}
      ref={ref}
      level={level}
      className={twMerge(displayLevels[displayLevel ?? level], className)}
    />
  );
});

export const SubHeading = React.forwardRef<
  HTMLDivElement,
  React.JSX.IntrinsicElements['div']
>(function SubHeading({ className, ...props }, ref) {
  return (
    <div
      {...props}
      ref={ref}
      className={twMerge('text-muted mt-2 text-base sm:text-sm/6', className)}
    />
  );
});
