import React from 'react';
import { twMerge } from 'tailwind-merge';
import { Heading, HeadingProps } from './heading';
import { composeRenderProps, TextProps } from 'react-aria-components';
import { Text } from './text';
import { Button, ButtonProps } from './button';
import { XIcon } from './icons/outline/x';

const CalloutContext = React.createContext<{
  'aria-labelledby': string;
  inline?: boolean;
  center?: boolean;
}>({
  'aria-labelledby': '',
  inline: false,
  center: false,
});

const colors = {
  zinc: [
    '[--callout-bg:var(--color-zinc-50)]',
    '[--callout-icon:var(--color-zinc-600)]',
    'dark:[--callout-bg:var(--color-zinc-400)]/10',
    'dark:[--callout-icon:var(--color-zinc-400)]',
  ],
  red: [
    '[--callout-bg:var(--color-red-50)]',
    '[--callout-border:var(--color-red-200)]',
    '[--callout-heading:var(--color-red-700)]',
    '[--callout-description:var(--color-red-700)]',
    '[--callout-icon:var(--color-red-600)]',

    'dark:[--callout-bg:var(--color-red-400)]/10',
    'dark:[--callout-border:var(--color-red-400)]/50',
    'dark:[--callout-heading:var(--color-red-200)]',
    'dark:[--callout-description:var(--color-red-300)]',
    'dark:[--callout-icon:var(--color-red-400)]',
  ],
  blue: [
    '[--callout-bg:var(--color-blue-50)]',
    '[--callout-border:var(--color-blue-200)]',
    '[--callout-heading:var(--color-blue-600)]',
    '[--callout-description:var(--color-blue-600)]',
    '[--callout-icon:var(--color-blue-500)]',

    'dark:[--callout-bg:var(--color-blue-400)]/10',
    'dark:[--callout-border:var(--color-blue-400)]/50',
    'dark:[--callout-heading:var(--color-blue-200)]',
    'dark:[--callout-description:var(--color-blue-300)]',
    'dark:[--callout-icon:var(--color-blue-400)]',
  ],
  yellow: [
    '[--callout-bg:var(--color-yellow-50)]',
    '[--callout-border:var(--color-yellow-200)]',
    '[--callout-heading:var(--color-yellow-700)]',
    '[--callout-description:var(--color-yellow-700)]',
    '[--callout-icon:var(--color-yellow-600)]',

    'dark:[--callout-bg:var(--color-yellow-400)]/10',
    'dark:[--callout-border:var(--color-yellow-400)]/50',
    'dark:[--callout-heading:var(--color-yellow-200)]',
    'dark:[--callout-description:var(--color-yellow-300)]',
    'dark:[--callout-icon:var(--color-yellow-400)]',
  ],
  green: [
    '[--callout-bg:var(--color-green-50)]',
    '[--callout-border:var(--color-green-200)]',
    '[--callout-heading:var(--color-green-700)]',
    '[--callout-description:var(--color-green-700)]',
    '[--callout-icon:var(--color-green-600)]',

    'dark:[--callout-bg:var(--color-green-400)]/10',
    'dark:[--callout-border:var(--color-green-400)]/50',
    'dark:[--callout-heading:var(--color-green-200)]',
    'dark:[--callout-description:var(--color-green-300)]',
    'dark:[--callout-icon:var(--color-green-400)]',
  ],
};

export type CalloutColor = keyof typeof colors;

type CalloutProps = {
  role?: React.AriaRole | null;
  compact?: boolean;
  children: React.ReactNode;
  color?: CalloutColor;
} & ({ inline?: never; center?: never } | { inline: true; center?: boolean }) &
  Omit<React.JSX.IntrinsicElements['div'], 'role'>;

export default function Callout({
  role,
  'aria-label': ariaLabel,
  inline,
  center,
  compact = false,
  color,
  className,
  ...props
}: CalloutProps) {
  const labelId = React.useId();

  return (
    <CalloutContext.Provider
      value={{ 'aria-labelledby': labelId, inline, center }}
    >
      <div
        {...(role !== null && { role: role ?? 'note' })}
        {...(ariaLabel
          ? { 'aria-label': ariaLabel }
          : role !== null && { 'aria-labelledby': labelId })}
        className={twMerge(
          '[--callout-icon:var(--color-muted)]',
          '[--callout-border:var(--color-border)]',
          '[--callout-description:var(--color-muted)]',

          'group border border-(--callout-border) bg-(--callout-bg)',
          'grid grid-cols-[1fr_auto_auto] items-center',

          center
            ? [
                'grid-cols-[auto_auto_auto] border-y p-2',
                'sm:flex sm:[&>:first-child]:ms-auto',
                'sm:[&>:last-child:not([data-ui=callout-control])]:me-auto',
                'sm:[&>[data-ui=callout-control]]:ms-auto',
              ]
            : 'max-w-lg rounded-xl border p-4',

          color && colors[color],

          !compact && [
            '[&:has([data-ui=callout-heading]>[data-ui=icon]:first-child)]:[--callout-indent:calc((--spacing(7)))]',
          ],

          '[&:has([data-ui=callout-heading]+[data-ui=callout-description])]:[--callout-content-row-end:3]',
          className,
        )}
        {...props}
      />
    </CalloutContext.Provider>
  );
}

export function CalloutHeading({
  displayLevel = 3,
  className,
  id,
  ...props
}: Omit<HeadingProps, 'level' | 'elementType'>) {
  const { 'aria-labelledby': ariaLabelledby, inline } =
    React.useContext(CalloutContext);

  return (
    <Heading
      {...props}
      id={id ?? ariaLabelledby}
      elementType="div"
      displayLevel={displayLevel}
      data-ui="callout-heading"
      className={twMerge(
        'col-start-1',
        '-col-end-2',
        inline && ['sm:-col-end-3'],
        'flex gap-x-2 gap-y-1 text-(--callout-heading)',
        '[&>[data-ui=icon]:first-child]:not([class*=text-])]:text-(--callout-icon)',
        '[&>[data-ui=icon]:first-child]:h-[1lh]',
        '[&>[data-ui=icon]:first-child]:w-5',
        '[&:has(+[data-ui=callout-description])]:mb-0.5',
        '[&:has([data-ui=badge]):has(+[data-ui=callout-description])]:mb-1',

        className,
      )}
    />
  );
}

export function CalloutDescription({ className, ...props }: TextProps) {
  const { inline } = React.useContext(CalloutContext);

  return (
    <Text
      {...props}
      data-ui="callout-description"
      className={twMerge(
        'text-(--callout-description)',
        'ps-(--callout-indent)',
        'col-start-1',
        '-col-end-2',
        inline && ['sm:-col-end-3'],
        className,
      )}
    />
  );
}

export function CalloutActions({
  className,
  ...props
}: React.JSX.IntrinsicElements['div']) {
  const { inline, center } = React.useContext(CalloutContext);

  return (
    <div
      {...props}
      data-ui="callout-actions"
      className={twMerge(
        'flex flex-wrap gap-2 ps-(--callout-indent)',
        'col-start-1',
        '-col-end-2',
        '[&>button]:text-nowrap',
        '[&:has([data-variant=link]:only-child)]:self-center',
        center ? 'py-1 sm:py-0' : 'pt-3',
        'hover:[&>[data-variant=plain]]:bg-transparent hover:[&>[data-variant=plain]]:text-(--callout-heading)',
        'hover:[&>[data-variant=link]]:text-(--callout-heading) hover:[&>[data-variant=link]]:decoration-(--callout-heading)',
        inline && [
          'sm:pt-0',
          'sm:ps-4',
          'sm:self-start',
          'sm:row-start-1',
          'sm:col-start-2',
          'sm:row-end-(--callout-content-row-end)',
        ],
        className,
      )}
    />
  );
}

export function CalloutControl({
  variant = 'plain',
  ...props
}: Omit<ButtonProps, 'children' | 'tooltip'>) {
  const { 'aria-label': ariaLabel, isIconOnly = true, ...restProps } = props;
  const { center } = React.useContext(CalloutContext);

  return (
    <div
      data-ui="callout-control"
      className={twMerge(
        '-col-start-1',
        'row-start-1',
        'row-end-(--callout-content-row-end)',
        'self-start',
        'ps-2',
        center && 'justify-self-end',
      )}
    >
      <Button
        {...restProps}
        isIconOnly={isIconOnly}
        variant={variant}
        className={composeRenderProps(props.className, (className) =>
          twMerge(
            'text-(--callout-icon)',
            'hover:bg-transparent',
            'hover:text-(--callout-heading)',
            'dark:hover:bg-transparent',
            className,
          ),
        )}
      >
        <XIcon aria-label={ariaLabel ?? 'Close'} />
      </Button>
    </div>
  );
}
