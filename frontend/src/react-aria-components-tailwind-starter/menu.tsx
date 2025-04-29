import React from 'react';
import {
  Menu as RACMenu,
  MenuItem as RACMenuItem,
  MenuProps as RACMenuProps,
  MenuItemProps as RACMenuItemProps,
  composeRenderProps,
  Separator,
  Header,
  MenuSectionProps as RACMenuSectionProps,
  MenuSection as RACMenuSection,
  Collection,
} from 'react-aria-components';
import { twMerge } from 'tailwind-merge';
import { Popover, PopoverProps } from './popover';
import { Button, ButtonProps } from './button';
import { composeTailwindRenderProps } from './utils';
import { Small } from './text';
import { CheckIcon } from './icons/outline/check';
import { ChevronDownIcon } from './icons/outline/chevron-down';
import { ChevronRightIcon } from './icons/outline/chevron-right';

export { MenuTrigger, SubmenuTrigger } from 'react-aria-components';

type MenuButtonProps = ButtonProps & {
  buttonArrow?: React.ReactNode;
};

export function MenuButton({
  buttonArrow = <ChevronDownIcon className="ms-auto" />,
  variant = 'outline',
  children,
  ...props
}: MenuButtonProps) {
  return (
    <Button {...props} variant={variant}>
      {(renderProps) => {
        return (
          <>
            {typeof children === 'function' ? children(renderProps) : children}
            {buttonArrow}
          </>
        );
      }}
    </Button>
  );
}

export const MenuPopover = React.forwardRef(
  ({ className, ...props }: PopoverProps, ref: React.Ref<HTMLDivElement>) => {
    return (
      <Popover
        {...props}
        ref={ref}
        className={composeTailwindRenderProps(
          className,
          twMerge(
            'max-w-72',
            'min-w-[max(--spacing(36),var(--trigger-width))]',
            'has-[[data-ui=content]_[data-ui=icon]]:min-w-[max(--spacing(48),var(--trigger-width))]',
            'has-[[data-ui=content]_kbd]:min-w-[max(--spacing(11),var(--trigger-width))]',
          ),
        )}
      />
    );
  },
);

type MenuProps<T> = RACMenuProps<T> & {
  checkIconPlacement?: 'start' | 'end';
};

export function Menu<T extends object>({
  checkIconPlacement = 'end',
  ...props
}: MenuProps<T>) {
  return (
    <RACMenu
      {...props}
      data-check-icon-placement={checkIconPlacement}
      className={composeTailwindRenderProps(
        props.className,
        twMerge(
          'max-h-[inherit] overflow-auto outline-hidden',
          'flex flex-col',
          'p-1 has-[header]:pt-0',

          // Header, Menu item style when has selectable items
          '[&_header]:px-2',

          checkIconPlacement === 'start' &&
            '[&:has(:is([role=menuitemradio],[role=menuitemcheckbox]))_:is(header,[role=menuitem])]:ps-7',

          // Menu item content
          '**:data-[ui=content]:flex-1',
          '**:data-[ui=content]:grid',
          '[&_[data-ui=content]:has([data-ui=label])]:grid-cols-[--spacing(4)_1fr_minmax(--spacing(12),max-content)]',
          '**:data-[ui=content]:items-center',
          '**:data-[ui=content]:gap-x-2',
          '**:data-[ui=content]:rtl:text-right',

          // Icon
          '[&_[data-ui=content]:not(:hover)>[data-ui=icon]:not([class*=text-])]:text-muted',
          '[&_[data-ui=content][data-destructive]>[data-ui=icon]]:text-red-600',
          '[&_[data-ui=content][data-destructive]:not(:hover)>[data-ui=icon]]:text-red-600/75',
          '[&_[data-ui=content]>[data-ui=icon]:not([class*=size-])]:size-4',
          '[&_[data-ui=content]>[data-ui=icon]:first-child]:col-start-1',

          // Label
          '**:data-[ui=label]:col-span-full',
          '[&:has([data-ui=icon]+[data-ui=label])_[data-ui=label]]:col-start-2',
          '[&:has([data-ui=kbd])_[data-ui=label]]:-col-end-2',
          '[&:has([data-ui=icon]+[data-ui=label])_[data-ui=content]:not(:has(>[data-ui=label]))]:ps-6',

          // Kbd
          '**:data-[ui=kbd]:col-span-1',
          '**:data-[ui=kbd]:row-start-1',
          '**:data-[ui=kbd]:col-start-3',
          '**:data-[ui=kbd]:justify-self-end',
          '**:data-[ui=kbd]:text-xs/6',
          '[&_:not([data-destructive])>[data-ui=kbd]:not([class*=bg-])]:text-muted/75',
          '[&_[data-destructive]>[data-ui=kbd]]:text-red-600',

          // Description
          '**:data-[ui=description]:col-span-full',
          '[&:has([data-ui=kbd])_[data-ui=description]]:-col-end-2',
          '[&:has([data-ui=icon]+[data-ui=label])_[data-ui=description]]:col-start-2',
        ),
      )}
    />
  );
}

export function SubMenu<T extends object>(
  props: MenuProps<T> & { 'aria-label': string },
) {
  return <Menu {...props} />;
}

export function MenuSeparator({ className }: { className?: string }) {
  return (
    <Separator
      className={twMerge(
        'border-t-border/50 my-1 w-[calc(100%-(--spacing(4)))] self-center border-t',
        className,
      )}
    />
  );
}

type MenuItemProps = RACMenuItemProps & {
  destructive?: true;
};

export function MenuItem({ destructive, ...props }: MenuItemProps) {
  const textValue =
    props.textValue ||
    (typeof props.children === 'string' ? props.children : undefined);

  return (
    <RACMenuItem
      {...props}
      textValue={textValue}
      className={composeRenderProps(
        props.className,
        (className, { isFocused, isDisabled }) => {
          return twMerge([
            'group rounded-sm outline-hidden',
            'flex items-center gap-x-1.5',
            'px-2 py-2.5 sm:py-1.5',
            'text-base/6 sm:text-sm/6',
            isDisabled && 'opacity-50',
            isFocused && 'bg-zinc-100 dark:bg-zinc-800',
            destructive && 'text-red-600',
            className,
          ]);
        },
      )}
    >
      {composeRenderProps(
        props.children,
        (children, { selectionMode, isSelected }) => (
          <>
            <CheckIcon
              className={twMerge(
                'flex h-[1lh] w-4 items-center self-start',
                selectionMode == 'none'
                  ? 'hidden'
                  : 'in-data-[check-icon-placement=end]:hidden',
                isSelected ? 'visible' : 'invisible',
              )}
            />
            <div
              data-ui="content"
              data-destructive={destructive ? destructive : undefined}
            >
              {children}
            </div>
            <CheckIcon
              className={twMerge(
                'flex h-[1lh] w-4 items-center self-start',
                selectionMode == 'none'
                  ? 'hidden'
                  : 'in-data-[check-icon-placement=start]:hidden',
                isSelected ? 'visible' : 'invisible',
              )}
            />

            {/* Submenu indicator */}
            <ChevronRightIcon className="text-muted hidden size-4 group-data-has-submenu:inline-block" />
          </>
        ),
      )}
    </RACMenuItem>
  );
}

export function MenuItemLabel({
  className,
  ...props
}: React.JSX.IntrinsicElements['span']) {
  return (
    <span
      slot="label"
      data-ui="label"
      className={twMerge('truncate', className)}
      {...props}
    />
  );
}

export function MenuItemDescription({
  className,
  ...props
}: React.JSX.IntrinsicElements['span']) {
  return (
    <Small
      slot="description"
      data-ui="description"
      className={className}
      {...props}
    />
  );
}

export interface MenuSectionProps<T> extends RACMenuSectionProps<T> {
  title?: string | React.ReactNode;
}

export function MenuSection<T extends object>({
  className,
  ...props
}: MenuSectionProps<T>) {
  return (
    <RACMenuSection
      {...props}
      className={twMerge(
        'not-first:mt-1.5',
        'not-first:border-t',
        'not-first:border-t-border/75',
        className,
      )}
    >
      <Header className="text-muted bg-background sticky inset-0 z-10 truncate pt-2 text-xs/6 rtl:text-right">
        {props.title}
      </Header>
      <Collection items={props.items}>{props.children}</Collection>
    </RACMenuSection>
  );
}
