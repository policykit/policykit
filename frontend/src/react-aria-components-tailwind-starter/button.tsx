import React from 'react';
import {
  Button as RACButton,
  ButtonProps as RACButtonProps,
  ToggleButton as RACToggleButton,
  ToggleButtonProps as RACToggleButtonProps,
  ToggleButtonGroup as RACToggleButtonGroup,
  ToggleButtonGroupProps,
  composeRenderProps,
} from 'react-aria-components';
import { twMerge } from 'tailwind-merge';
import { AsChildProps, Slot } from './slot';
import { SpinnerIcon } from './icons/outline/spinner';
import { NonFousableTooltipTarget, Tooltip, TooltipTrigger } from './tooltip';

type Color = 'accent' | 'red' | 'green';

type Size = 'sm' | 'lg';

type Variant = 'solid' | 'outline' | 'plain' | 'link' | 'unstyle';

export type ButtonStyleProps = {
  color?: Color;
  size?: Size;
  isCustomPending?: boolean;
  isIconOnly?: boolean;
  pendingLabel?: string;
  variant?: Variant;
};

export type ButtonWithAsChildProps = AsChildProps<
  RACButtonProps & {
    tooltip?: string | React.ReactElement;
    allowTooltipOnDisabled?: boolean;
  }
> &
  ButtonStyleProps;

export type ButtonProps = RACButtonProps &
  ButtonStyleProps & {
    tooltip?: string | React.ReactElement;
  };

const buttonStyle = ({
  size,
  color,
  isIconOnly,
  variant = 'solid',
  isPending,
  isDisabled,
  isFocusVisible,
  isCustomPending,
}: ButtonStyleProps & {
  isPending?: boolean;
  isDisabled?: boolean;
  isFocusVisible?: boolean;
}) => {
  const base = [
    'relative rounded-md',
    isFocusVisible
      ? 'outline outline-2 outline-ring outline-offset-2'
      : 'outline-hidden',
    isDisabled && 'opacity-50',
  ];

  if (variant === 'unstyle') {
    return base;
  }

  const style = {
    base,
    variant: {
      base: 'group inline-flex gap-x-2 justify-center items-center font-semibold text-base/6 sm:text-sm/6',
      solid: [
        'bg-[var(--btn-bg)]',
        color === 'red' || color === 'green'
          ? '[--btn-color:white]'
          : '[--btn-color:lch(from_var(--btn-bg)_calc((49.44_-_l)_*_infinity)_0_0)]',
        'text-[var(--btn-color)]',
        !isDisabled && 'hover:opacity-90',
      ],
      outline: [
        'text-[var(--btn-color)]',
        'shadow-outline',
        'in-[[data-ui=button-group]]:shadow-none',
        'dark:in-[[data-ui=button-group]]:shadow-none',
        'bg-white dark:bg-white/5',
        !isDisabled && 'hover:bg-zinc-50 dark:hover:bg-zinc-800',
      ],
      plain: [
        'text-[var(--btn-color)]',
        !isDisabled && 'hover:bg-zinc-100 dark:hover:bg-zinc-800',
      ],
      link: [
        'text-[var(--btn-color)] underline [&:not(:hover)]:decoration-[var(--btn-color)]/20 underline-offset-4',
      ],
    },
    size: {
      base: '[&_svg[data-ui=icon]:not([class*=size-])]:size-[var(--icon-size)]',
      sm: [
        isIconOnly
          ? 'size-8 sm:size-7 [--icon-size:theme(size.5)] sm:[--icon-size:theme(size.4)]'
          : variant !== 'link' &&
            'h-8 sm:h-7 [--icon-size:theme(size.3)] text-sm/6 sm:text-xs/6 px-3 sm:px-2',
      ],
      md: [
        // lg: 44px, sm:36px
        '[--icon-size:theme(size.5)] sm:[--icon-size:theme(size.4)]',
        isIconOnly
          ? 'p-2.5 sm:p-1.5 [&_svg[data-ui=icon]]:m-0.5 sm:[&_svg[data-ui=icon]]:m-1'
          : variant !== 'link' && 'px-3.5 sm:px-3 py-2.5 sm:py-1.5',
      ],

      lg: [
        '[--icon-size:theme(size.5)]',
        isIconOnly
          ? 'p-2.5 [&_svg[data-ui=icon]]:m-0.5'
          : variant !== 'link' && 'px-3.5 py-2.5',
      ],
    },
    color: {
      foreground: '[--btn-color:var(--color-foreground)]',
      accent: '[--btn-color:var(--color-accent)]',
      red: '[--btn-color:var(--color-red-600)]',
      green: '[--btn-color:var(--color-green-600)]',
    },
    iconColor: {
      base: isPending
        ? '[&_svg[data-ui=icon]:not([class*=text-])]:text-[var(--icon-color)]'
        : '[&:not(:hover)_svg[data-ui=icon]:not([class*=text-])]:text-[var(--icon-color)]',
      solid: !isIconOnly && '[--icon-color:var(--btn-color)]/75',
      outline: !isIconOnly && '[--icon-color:var(--color-muted)]/50',
      plain: !isIconOnly && '[--icon-color:var(--color-muted)]/50',
      link: !isIconOnly && '[--icon-color:var(--btn-color)]',
    },
    backgroundColor: {
      accent: '[--btn-bg:var(--color-accent)]',
      red: '[--btn-bg:var(--color-red-600)]',
      green: '[--btn-bg:var(--color-green-600)]',
    },
  };

  return [
    style.base,
    style.color[color ?? 'foreground'],
    style.size.base,
    style.size[size ?? 'md'],
    style.iconColor.base,
    style.iconColor[variant],
    style.backgroundColor[color ?? 'accent'],
    style.variant.base,
    style.variant[variant],
    !isCustomPending && isPending && 'text-transparent',
  ];
};

export const Button = React.forwardRef<
  HTMLButtonElement,
  ButtonWithAsChildProps
>(function Button(props, ref) {
  if (props.asChild) {
    return (
      <Slot className={twMerge(buttonStyle(props))}>{props.children}</Slot>
    );
  }

  const {
    asChild,
    tooltip,
    allowTooltipOnDisabled,
    children,
    isCustomPending,
    pendingLabel,
    size,
    color,
    variant = 'solid',
    isIconOnly,
    ...buttonProps
  } = props;

  const button = (
    <RACButton
      {...buttonProps}
      ref={ref}
      data-variant={variant}
      className={composeRenderProps(props.className, (className, renderProps) =>
        twMerge([
          buttonStyle({
            size,
            color,
            isIconOnly,
            variant,
            isCustomPending,
            ...renderProps,
          }),
          className,
        ]),
      )}
    >
      {(renderProps) => {
        return (
          <>
            {renderProps.isPending ? (
              <>
                <SpinnerIcon
                  aria-label={pendingLabel}
                  className={twMerge(
                    'absolute',
                    isCustomPending ? 'sr-only' : 'flex',
                  )}
                />
                <span
                  className="contents"
                  {...(renderProps.isPending && { 'aria-hidden': true })}
                >
                  {typeof children === 'function'
                    ? children(renderProps)
                    : children}
                </span>
              </>
            ) : typeof children === 'function' ? (
              children(renderProps)
            ) : (
              children
            )}
          </>
        );
      }}
    </RACButton>
  );

  if (tooltip) {
    if (allowTooltipOnDisabled && buttonProps.isDisabled) {
      return (
        <TooltipTrigger>
          <NonFousableTooltipTarget>
            <div className="content">{button}</div>
          </NonFousableTooltipTarget>
          {typeof tooltip === 'string' ? <Tooltip>{tooltip}</Tooltip> : tooltip}
        </TooltipTrigger>
      );
    }

    return (
      <TooltipTrigger>
        {button}
        {typeof tooltip === 'string' ? <Tooltip>{tooltip}</Tooltip> : tooltip}
      </TooltipTrigger>
    );
  }

  return button;
});

export function ToggleButton(
  props: RACToggleButtonProps &
    ButtonStyleProps & {
      tooltip?: React.ReactNode;
      allowTooltipOnDisabled?: boolean;
    },
) {
  const {
    variant,
    tooltip,
    allowTooltipOnDisabled,
    size,
    isIconOnly,
    color,
    ...buttonProps
  } = props;

  const toggleButton = (
    <RACToggleButton
      {...buttonProps}
      data-variant={variant}
      className={composeRenderProps(
        props.className,
        (className, renderProps) => {
          return twMerge(
            buttonStyle({ variant, size, isIconOnly, color, ...renderProps }),
            className,
          );
        },
      )}
    />
  );

  if (tooltip) {
    if (allowTooltipOnDisabled && buttonProps.isDisabled) {
      return (
        <TooltipTrigger>
          <NonFousableTooltipTarget>
            <div className="content">{toggleButton}</div>
          </NonFousableTooltipTarget>
          {tooltip}
        </TooltipTrigger>
      );
    }

    return (
      <TooltipTrigger>
        {toggleButton}
        {tooltip}
      </TooltipTrigger>
    );
  }

  return toggleButton;
}

const buttonGroupStyle = ({
  inline,
  orientation = 'horizontal',
}: {
  inline?: boolean;
  orientation?: 'horizontal' | 'vertical';
}) => {
  const style = {
    base: [
      'group inline-flex w-max items-center',
      '[&>*:not(:first-child):not(:last-child)]:rounded-none',
      '[&>*[data-variant=solid]:not(:first-child)]:border-s',
      '[&>*[data-variant=solid]:not(:first-child)]:border-s-[oklch(from_var(--btn-bg)_calc(l*0.85)_c_h)]',

      '[&:has([data-variant=outline])]:rounded-md',
      '[&:has([data-variant=outline])]:shadow-outline',
      'dark:[&:has([data-variant=outline])]:p-px',
      'dark:[&:has([data-variant=outline])]:bg-white/5',
      'dark:[&:has([data-variant=outline])]:rounded-[calc(var(--radius-md)+1px)]',
      'dark:[&:has([data-variant=outline])>[data-variant=outline]]:[--color-border:oklch(1_0_0_/_0.05)]',
    ],
    horizontal: [
      '[&>*:first-child]:rounded-e-none',
      '[&>*:last-child]:rounded-s-none',
      !inline && '[&:has([data-variant=outline])>*:not(:first-child)]:border-s',
    ],
    vertical: [
      'flex-col',
      '[&>*:first-child]:rounded-b-none',
      '[&>*:last-child]:rounded-t-none',
      !inline && '[&:has([data-variant=outline])>*:not(:first-child)]:border-t',
    ],
  };

  return [style.base, style[orientation]];
};

export function ToggleButtonGroup({
  inline,
  orientation = 'horizontal',
  ...props
}: ToggleButtonGroupProps & {
  inline?: boolean;
  orientation?: 'horizontal' | 'vertical';
}) {
  return (
    <RACToggleButtonGroup
      {...props}
      data-ui="button-group"
      className={composeRenderProps(props.className, (className) =>
        twMerge(buttonGroupStyle({ inline, orientation }), className),
      )}
    />
  );
}

export function ButtonGroup({
  className,
  inline,
  orientation = 'horizontal',
  ...props
}: React.JSX.IntrinsicElements['div'] & {
  inline?: boolean;
  orientation?: 'horizontal' | 'vertical';
}) {
  return (
    <div
      {...props}
      data-ui="button-group"
      className={twMerge(buttonGroupStyle({ inline, orientation }), className)}
    />
  );
}
