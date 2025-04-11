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
import { SpinnerIcon } from './icons';
import { NonFousableTooltipTarget, TooltipTrigger } from './tooltip';

type Color = 'accent' | 'success' | 'destructive';

type Size = 'sm' | 'lg';

type Variant = 'solid' | 'outline' | 'plain' | 'unstyle';

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
    tooltip?: React.ReactNode;
    allowTooltipOnDisabled?: boolean;
  }
> &
  ButtonStyleProps;

export type ButtonProps = RACButtonProps &
  ButtonStyleProps & {
    tooltip?: React.ReactNode;
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
        'border border-transparent bg-[var(--btn-bg)]',
        '[--btn-color:lch(from_var(--btn-bg)_calc((49.44_-_l)_*_infinity)_0_0)]',
        'text-[var(--btn-color)]',
        !isDisabled && 'hover:opacity-90',
      ],
      outline: [
        'border text-[var(--btn-color)] shadow-xs',
        !isDisabled && 'hover:bg-zinc-50 dark:hover:bg-zinc-800',
      ],
      plain: [
        'text-[var(--btn-color)]',
        !isDisabled && 'hover:bg-zinc-100 dark:hover:bg-zinc-800',
      ],
    },
    size: {
      base: '[&_svg[data-ui=icon]:not([class*=size-])]:size-[var(--icon-size)]',
      sm: [
        isIconOnly
          ? 'size-8 sm:size-7 [--icon-size:theme(size.5)] sm:[--icon-size:theme(size.4)]'
          : 'h-8 sm:h-7 [--icon-size:theme(size.3)] text-sm/6 sm:text-xs/6 px-3 sm:px-2',
      ],
      md: [
        // lg: 44px, sm:36px
        '[--icon-size:theme(size.5)] sm:[--icon-size:theme(size.4)]',
        isIconOnly
          ? 'p-[calc(--spacing(2.5)-1px)] sm:p-[calc(--spacing(1.5)-1px)] [&_svg[data-ui=icon]]:m-0.5 sm:[&_svg[data-ui=icon]]:m-1'
          : 'px-[calc(--spacing(3.5)-1px)] sm:px-[calc(--spacing(3)-1px)] py-[calc(--spacing(2.5)-1px)] sm:py-[calc(--spacing(1.5)-1px)]',
      ],

      lg: [
        '[--icon-size:theme(size.5)]',
        isIconOnly
          ? 'p-[calc(--spacing(2.5)-1px)] [&_svg[data-ui=icon]]:m-0.5'
          : 'px-[calc(--spacing(3.5)-1px)] py-[calc(--spacing(2.5)-1px)]',
      ],
    },
    color: {
      foreground: '[--btn-color:var(--color-foreground)]',
      accent: '[--btn-color:var(--color-accent)]',
      destructive: '[--btn-color:var(--color-destructive)]',
      success: '[--btn-color:var(--color-success)]',
    },
    iconColor: {
      base: '[&:not(:hover)_svg[data-ui=icon]:not([class*=text-])]:text-[var(--icon-color)]',
      solid:
        !isIconOnly &&
        '[--icon-color:lch(from_var(--btn-color)_calc(0.85*l)_c_h)]',
      outline: !isIconOnly && '[--icon-color:var(--color-muted)]',
      plain: !isIconOnly && '[--icon-color:var(--color-muted)]',
    },
    backgroundColor: {
      accent: '[--btn-bg:var(--color-accent)]',
      destructive: '[--btn-bg:var(--color-destructive)]',
      success: '[--btn-bg:var(--color-success)]',
    },
  };

  return [
    style.base,
    style.color[color ?? 'foreground'],
    style.variant.base,
    style.variant[variant],
    style.size.base,
    style.size[size ?? 'md'],
    style.iconColor.base,
    style.iconColor[variant],
    style.backgroundColor[color ?? 'accent'],
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
          {tooltip}
        </TooltipTrigger>
      );
    }

    return (
      <TooltipTrigger>
        {button}
        {tooltip}
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
      '[&>*[data-variant=solid]:not(:first-child)]:border-s-[lch(from_var(--btn-bg)_calc(l*0.85)_c_h)]',
    ],
    horizontal: [
      '[&>*:first-child]:rounded-e-none',
      '[&>*:last-child]:rounded-s-none',
      '[&>*:not(:last-child)]:border-e-0',
      inline && 'shadow-xs [&>*:not(:first-child)]:border-s-0 *:shadow-none',
    ],
    vertical: [
      'flex-col',
      '[&>*:first-child]:rounded-b-none',
      '[&>*:last-child]:rounded-t-none',
      '[&>*:not(:last-child)]:border-b-0',

      inline && 'shadow-xs [&>*:not(:first-child)]:border-t-0 *:shadow-none',
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
