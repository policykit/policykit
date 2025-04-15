import { twMerge } from 'tailwind-merge';

type DotVariantProps = {
  variant: 'dot';
  inline?: boolean;
};

type NumericVariantProps = {
  variant: 'numeric';
  value: number;
  inline?: boolean;
};

export type NotificationBadgeProps = (DotVariantProps | NumericVariantProps) &
  React.JSX.IntrinsicElements['span'];

export function NotificationBadge({
  className,
  'aria-label': ariaLabel,
  ...props
}: NotificationBadgeProps) {
  if (props.variant === 'dot') {
    const { variant, inline, ...rest } = props;

    return (
      <>
        <span
          data-ui="notification-badge"
          {...(ariaLabel
            ? { 'aria-label': ariaLabel }
            : { 'aria-hidden': true })}
          className={twMerge(
            inline ? '' : 'absolute top-1 right-1',
            'flex size-2 rounded-full bg-red-600',
            className,
          )}
        />
        {ariaLabel && (
          <span role="status" className="sr-only" {...rest}>
            {ariaLabel}
          </span>
        )}
      </>
    );
  }

  const { value, variant, inline, ...rest } = props;

  return (
    <>
      <span
        data-ui="notification-badge"
        {...(ariaLabel ? { 'aria-label': ariaLabel } : { 'aria-hidden': true })}
        className={twMerge([
          inline ? '' : 'absolute -top-1.5 -right-1',
          'flex h-4 items-center justify-center rounded-full bg-red-600 text-[0.65rem] text-white',
          props.value > 0 ? (props.value > 9 ? 'w-5' : 'w-4') : 'hidden',
          className,
        ])}
      >
        {Math.min(props.value, 9)}
        {props.value > 9 ? <span className="pb-0.5">+</span> : null}
      </span>

      {ariaLabel && (
        <>
          <span className="sr-only">{ariaLabel}</span>
          <span role="status" className="sr-only" {...rest}>
            {ariaLabel}
          </span>
        </>
      )}
    </>
  );
}
