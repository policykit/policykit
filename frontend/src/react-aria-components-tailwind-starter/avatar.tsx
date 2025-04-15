import React from 'react';
import { FallbackAvatarProps, getFallbackAvatarDataUrl } from './initials';
import { twMerge } from 'tailwind-merge';
import { useImageLoadingStatus } from './hooks/use-image-loading-status';

const AvatarContext = React.createContext<{
  badgeId: string;
} | null>(null);

export type AvatarProps = {
  src?: string;
  alt: string;
} & FallbackAvatarProps &
  React.JSX.IntrinsicElements['div'];

export function Avatar({
  className,
  children,
  src,
  alt,
  fallback = 'initials',
  colorful,
  background,
  ...props
}: AvatarProps) {
  const badgeId = React.useId();
  const avatarId = React.useId();
  const ariaLabelledby = [avatarId, children ? badgeId : ''].join(' ');
  const status = useImageLoadingStatus(src);

  return (
    <AvatarContext.Provider value={{ badgeId }}>
      <div
        {...props}
        role="img"
        className={twMerge([
          'group ring-background @container relative isolate flex size-10 shrink-0',
          status ==='loaded' &&  'dark:outline dark:-outline-offset-1 dark:outline-white/10',
          '[--border-radius:var(--radius-lg)]',
          '[&.rounded-full]:[--border-radius:calc(infinity_*_1px)]',
          'rounded-[radius:var(--border-radius)]',
          '[&>img]:rounded-[var(--border-radius)]',
          '[&>img]:size-full',
          className,
        ])}
        aria-labelledby={ariaLabelledby}
      >
        <img
          aria-hidden
          id={avatarId}
          src={
            status === 'error'
              ? getFallbackAvatarDataUrl({
                  fallback,
                  alt,
                  ...(colorful === undefined ? { background } : { colorful }),
                })
              : src
          }
          alt={alt}
          className={twMerge(
            'object-cover',
            // size
            '[--badge-size:8px] [&+[data-ui=avatar-badge]]:[--badge-size:8px]',
            '@[32px]:[--badge-size:10px] @[32px]:[&+[data-ui=avatar-badge]]:[--badge-size:10px]',
            '@[48px]:[--badge-size:12px] @[48px]:[&+[data-ui=avatar-badge]]:[--badge-size:12px]',
            '@[64px]:[--badge-size:16px] @[64px]:[&+[data-ui=avatar-badge]]:[--badge-size:16px]',
            '@[96px]:[--badge-size:20px] @[96px]:[&+[data-ui=avatar-badge]]:[--badge-size:20px]',
            '@[120px]:[--badge-size:24px] @[120px]:[&+[data-ui=avatar-badge]]:[--badge-size:24px]',
            '@[128px]:[--badge-size:26px] @[128px]:[&+[data-ui=avatar-badge]]:[--badge-size:26px]',
            '[--badge-gap:2px]',
            '@[120px]:[--badge-gap:3px]',
            '[&:has(+[data-ui=avatar-badge])]:[mask:radial-gradient(circle_at_bottom_calc(var(--badge-size)/2)_right_calc(var(--badge-size)/2),_transparent_calc(var(--badge-size)/2_+_var(--badge-gap)_-_0.25px),_white_calc(var(--badge-size)/2_+_var(--badge-gap)_+_0.25px))]',
            '[&+[data-ui=avatar-badge]:not([class*=size-])]:size-(--badge-size)',
            '[&+[data-ui=avatar-badge]>[data-ui=icon]:not([class*=size-])]:size-full',
          )}
        />
        {children}
      </div>
    </AvatarContext.Provider>
  );
}

type AvatarBadgeProps = {
  className?: string;
  badge: React.ReactNode;
};

export const AvatarBadge = ({ badge, ...props }: AvatarBadgeProps) => {
  const context = React.useContext(AvatarContext);

  if (!context) {
    throw new Error('<AvatarContext.Provider> is required');
  }

  return (
    <span
      aria-hidden
      data-ui="avatar-badge"
      id={context.badgeId}
      className={twMerge([
        'bg-background absolute end-0 bottom-0 grid place-items-center rounded-full bg-clip-content',
        props.className,
      ])}
    >
      {badge}
    </span>
  );
};

type AvatarGroupProps = {
  reverse?: boolean;
} & React.JSX.IntrinsicElements['div'];

export function AvatarGroup({
  reverse = false,
  className,
  ...props
}: AvatarGroupProps) {
  return (
    <div
      {...props}
      className={twMerge(
        'isolate flex items-center -space-x-2 rtl:space-x-reverse',
        '[&>[role=img]:not([class*=ring-4])]:ring-2',
        reverse &&
          'flex-row-reverse justify-end [&>[role=img]:last-of-type]:-me-2',
        className,
      )}
    />
  );
}
