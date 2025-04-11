import {
  DialogProps as RACDialogProps,
  Dialog as RACDialog,
  composeRenderProps,
} from 'react-aria-components';
import { twMerge } from 'tailwind-merge';
import React from 'react';
import { BaseHeadingProps, Heading } from './heading';
import { Button, ButtonProps } from './button';
import { Text } from './text';
import { XIcon } from './icons';

export { DialogTrigger } from 'react-aria-components';

export interface DialogProps extends RACDialogProps {
  alert?: boolean;
}

export function Dialog({ role, alert = false, ...props }: DialogProps) {
  return (
    <RACDialog
      {...props}
      role={role ?? alert ? 'alertdialog' : 'dialog'}
      className={twMerge(
        'relative flex max-h-[inherit] flex-col overflow-auto outline-hidden [&:has([data-ui=dialog-body])]:overflow-hidden',
        '[&:not(:has([data-ui=dialog-header]))>[data-ui=dialog-body]:not([class*=pt-])]:pt-6',
        '[&:not(:has([data-ui=dialog-footer]))>[data-ui=dialog-body]:not([class*=pt-])]:pb-6',
        props.className,
      )}
    />
  );
}

type DialogHeaderProps = BaseHeadingProps;

export const DialogTitle = React.forwardRef<
  HTMLHeadingElement,
  DialogHeaderProps
>(function DialogTitle({ level = 2, ...props }, ref) {
  return <Heading {...props} ref={ref} slot="title" level={level} />;
});

export function DialogHeader({ className, ...props }: DialogHeaderProps) {
  const headerRef = React.useRef<HTMLHeadingElement>(null);

  React.useEffect(() => {
    const header = headerRef.current;
    if (!header) {
      return;
    }

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        header.parentElement?.style.setProperty(
          '--dialog-header-height',
          `${entry.target.clientHeight}px`,
        );
      }
    });

    observer.observe(header);

    return () => {
      observer.unobserve(header);
    };
  }, []);

  return React.Children.toArray(props.children).every(
    (child) => typeof child === 'string',
  ) ? (
    <DialogTitle
      {...props}
      data-ui="dialog-header"
      ref={headerRef}
      className={twMerge('ps-6 pe-10 pt-6 pb-2', className)}
    />
  ) : (
    <div
      ref={headerRef}
      data-ui="dialog-header"
      className={twMerge(
        'relative flex w-full flex-col ps-6 pe-10 pt-6 pb-2',
        className,
      )}
      {...props}
    >
      {props.children}
    </div>
  );
}

export function DialogBody({
  className,
  children,
  ...props
}: React.JSX.IntrinsicElements['div']) {
  return (
    <div
      {...props}
      data-ui="dialog-body"
      className={twMerge(
        'flex flex-1 flex-col overflow-auto px-6',
        'max-h-[calc(var(--visual-viewport-height)-var(--visual-viewport-vertical-padding)-var(--dialog-header-height,0px)-var(--dialog-footer-height,0px))]',
        className,
      )}
    >
      {React.Children.toArray(children).every(
        (child) => typeof child === 'string',
      ) ? (
        <Text>{children}</Text>
      ) : (
        children
      )}
    </div>
  );
}

export function DialogFooter({
  className,
  ...props
}: React.JSX.IntrinsicElements['div']) {
  const footerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const footer = footerRef.current;

    if (!footer) {
      return;
    }

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        footer.parentElement?.style.setProperty(
          '--dialog-footer-height',
          `${entry.target.clientHeight}px`,
        );
      }
    });

    observer.observe(footer);
    return () => {
      observer.unobserve(footer);
    };
  }, []);

  return (
    <div
      {...props}
      data-ui="dialog-footer"
      ref={footerRef}
      className={twMerge(
        'mt-auto flex flex-col flex-col-reverse justify-end gap-3 p-6 sm:flex-row',
        className,
      )}
    />
  );
}

export function DialogCloseButton({
  variant = 'plain',
  ...props
}: ButtonProps) {
  if (props.children) {
    return <Button {...props} slot="close" variant={variant} />;
  }

  const {
    size = 'lg',
    'aria-label': ariaLabel,
    isIconOnly = true,
    ...restProps
  } = props;

  return (
    <Button
      {...restProps}
      slot="close"
      isIconOnly={isIconOnly}
      variant={variant}
      size={size}
      className={composeRenderProps(props.className, (className) =>
        twMerge(
          'text-muted/75 hover:text-foreground absolute end-2 top-3 p-1.5',
          className,
        ),
      )}
    >
      <XIcon aria-label={ariaLabel ?? 'Close'} />
    </Button>
  );
}
