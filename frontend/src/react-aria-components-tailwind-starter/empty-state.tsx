import { twMerge } from 'tailwind-merge';
import { TextProps } from 'react-aria-components';
import { Text } from './text';
import { Heading, HeadingProps } from './heading';

export function EmptyState({
  className,
  ...props
}: React.JSX.IntrinsicElements['div']) {
  return (
    <div
      {...props}
      className={twMerge(
        '@container flex h-full w-full flex-col items-center justify-center gap-1 p-4 text-center',
        className,
      )}
    />
  );
}

export function EmptyStateIcon({
  className,
  children,
  ...props
}: React.JSX.IntrinsicElements['div']) {
  return (
    <div
      {...props}
      className={twMerge(
        'mb-2 flex max-w-32 items-center justify-center @md:max-w-40',
        '[&>svg:not([class*=text-])]:text-muted [&>svg]:h-auto [&>svg]:max-w-full [&>svg]:min-w-12',
        className,
      )}
    >
      {children}
    </div>
  );
}

export function EmptyStateHeading({
  className,
  level = 2,
  displayLevel,
  elementType,
  ...props
}: HeadingProps) {
  if (elementType && !displayLevel) {
    displayLevel = 2;
  }
  
  return (
    <Heading
      {...props}
      displayLevel={displayLevel}
      {...(elementType
        ? { elementType }
        : {
            level: level,
          })}
      className={twMerge('text-balance', className)}
    />
  );
}

export function EmptyStateDescription({ className, ...props }: TextProps) {
  return (
    <Text
      {...props}
      className={twMerge('max-w-prose text-balance', className)}
    />
  );
}

export function EmptyStateActions({
  className,
  ...props
}: React.JSX.IntrinsicElements['div']) {
  return (
    <div
      {...props}
      className={twMerge(
        'mt-3 flex flex-col items-center justify-center gap-4 p-2',
        className,
      )}
    />
  );
}
