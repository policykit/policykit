import React from 'react';
import {
  ModalOverlay as RACModalOverlay,
  ModalOverlayProps as RACModalOverlayProps,
  Modal as RACModal,
} from 'react-aria-components';
import { composeTailwindRenderProps } from './utils';

const sizes = {
  xs: 'sm:max-w-xs',
  sm: 'sm:max-w-sm',
  md: 'sm:max-w-md',
  lg: 'sm:max-w-lg',
  xl: 'sm:max-w-lg',
  '2xl': 'sm:max-w-2xl',
  '3xl': 'sm:max-w-3xl',
  '4xl': 'sm:max-w-4xl',
  '5xl': 'sm:max-w-5xl',
  fullWidth: 'w-full',
};

type ModalType =
  | { drawer?: never; placement?: 'center' | 'top' }
  | { drawer: true; placement?: 'left' | 'right' };

type ModalProps = Omit<RACModalOverlayProps, 'className'> & {
  size?: keyof typeof sizes;
  classNames?: {
    modalOverlay?: RACModalOverlayProps['className'];
    modal?: RACModalOverlayProps['className'];
  };
} & ModalType;

export function Modal({ classNames, ...props }: ModalProps) {
  const drawer = props.drawer;
  const placement = props.drawer ? props.placement ?? 'left' : props.placement;

  React.useEffect(() => {
    document
      .querySelector<HTMLElement>(':root')
      ?.style.setProperty(
        '--scrollbar-width',
        `${window.innerWidth - document.documentElement.clientWidth}px`,
      );
  }, []);

  return (
    <RACModalOverlay
      {...props}
      data-ui="modal-overlay"
      className={composeTailwindRenderProps(classNames?.modalOverlay, [
        'fixed top-0 left-0 isolate z-20',
        'h-(--visual-viewport-height) w-full',
        'bg-zinc-950/25 dark:bg-zinc-950/50',
        'text-center',
        'data-entering:animate-in',
        'data-entering:fade-in',
        'data-entering:duration-300',
        'data-entering:ease-out',
        'data-exiting:animate-out',
        'data-exiting:fade-out',
        'data-exiting:duration-200',
        'data-exiting:ease-in',

        drawer
          ? 'flex items-start p-2 [--visual-viewport-vertical-padding:16px] [&:has([data-placement=right])]:justify-end'
          : [
              'grid justify-items-center',
              placement === 'center'
                ? 'grid-rows-[1fr_auto_1fr] p-4 [--visual-viewport-vertical-padding:32px]'
                : [
                    // Default alert dialog style
                    '[&:has([role=alertdialog])]:grid-rows-[1fr_auto_1fr] sm:[&:has([role=alertdialog])]:grid-rows-[1fr_auto_3fr]',
                    '[&:has([role=alertdialog])]:p-4 [&:has([role=alertdialog])]:[--visual-viewport-vertical-padding:32px]',

                    // Default dialog style
                    placement === 'top'
                      ? 'grid-rows-[1fr_auto_3fr] [&:has([role=dialog])]:p-4 sm:[&:has([role=dialog])]:[--visual-viewport-vertical-padding:32px]'
                      : [
                          'grid-rows-[1fr_auto] sm:grid-rows-[1fr_auto_3fr]',
                          '[&:has([role=dialog])]:pt-4 sm:[&:has([role=dialog])]:p-4',
                          '[&:has([role=dialog])]:[--visual-viewport-vertical-padding:16px]',
                          'sm:[&:has([role=dialog])]:[--visual-viewport-vertical-padding:32px]',
                        ],
                  ],

              /**
               * Style for stack dialogs
               */
              // First dialog
              '[&:has(~[data-ui=modal-overlay]:not([data-exiting]))>[data-ui=modal]>section]:opacity-75',
              '[&:has(~[data-ui=modal-overlay]:not([data-exiting]))>[data-ui=modal]]:bg-zinc-100',
              'dark:[&:has(~[data-ui=modal-overlay]:not([data-exiting]))>[data-ui=modal]]:bg-zinc-900',

              '[&:has(~[data-ui=modal-overlay])>[data-ui=modal]]:transform-[scale,y]',
              '[&:has(~[data-ui=modal-overlay])>[data-ui=modal]]:ease-in-out',
              '[&:has(~[data-ui=modal-overlay])>[data-ui=modal]]:duration-200',

              // When the nested dialog is not closing
              '[&:has(~[data-ui=modal-overlay]:not([data-exiting]))>[data-ui=modal]]:scale-90',
              // Remove nested dialog overlay background and fade in effect
              '[&:has(~[data-ui=modal-overlay])~[data-ui=modal-overlay]]:bg-transparent',
              '[&:has(~[data-ui=modal-overlay])~[data-ui=modal-overlay]]:fade-in-100',

              // Make both dialogs close immediately
              '[&:has(~[data-ui=modal-overlay])~[data-ui=modal-overlay][data-exiting]]:opacity-0',
              '[&[data-exiting]:has(~[data-ui=modal-overlay])]:opacity-0',
            ],
      ])}
    >
      <RACModal
        {...props}
        data-ui="modal"
        data-placement={placement}
        className={composeTailwindRenderProps(classNames?.modal, [
          'relative max-h-full w-full overflow-hidden',
          'text-left align-middle',
          'shadow-lg',
          'bg-background',
          'ring-1 ring-zinc-950/5 dark:ring-zinc-800',

          props.size
            ? sizes[props.size]
            : 'sm:has-[[role=alertdialog]]:max-w-md sm:has-[[role=dialog]]:max-w-lg',

          'data-entering:animate-in',
          'data-entering:ease-out',
          'data-entering:duration-200',
          'data-exiting:animate-out',
          'data-exiting:ease-in',
          'data-exiting:duration-200',

          drawer
            ? [
                'h-full',
                'rounded-xl',
                'data-[placement=left]:data-entering:slide-in-from-left',
                'data-[placement=right]:data-entering:slide-in-from-right',
                'data-[placement=left]:data-exiting:slide-out-to-left',
                'data-[placement=right]:data-exiting:slide-out-to-right',
              ]
            : [
                'row-start-2',
                'rounded-xl',
                'data-entering:zoom-in-95',
                'data-exiting:zoom-out-95',

                // Handle layout shift when toggling scroll lock
                props.size !== 'fullWidth' &&
                  'sm:data-exiting:-me-(--scrollbar-width)',
                'sm:data-exiting:duration-0',

                !placement && [
                  'has-[[role=dialog]]:rounded-t-xl',
                  'has-[[role=dialog]]:rounded-b-none',
                  'sm:has-[[role=dialog]]:rounded-xl',

                  'has-[[role=dialog]]:data-entering:zoom-in-100',
                  'has-[[role=dialog]]:data-entering:slide-in-from-bottom',
                  'sm:has-[[role=dialog]]:data-entering:zoom-in-95',
                  'sm:has-[[role=dialog]]:data-entering:slide-in-from-bottom-0',

                  'has-[[role=dialog]]:data-exiting:zoom-out-100',
                  'has-[[role=dialog]]:data-exiting:slide-out-to-bottom',
                  'sm:has-[[role=dialog]]:data-exiting:zoom-out-95',
                  'sm:has-[[role=dialog]]:data-exiting:slide-out-to-bottom-0',
                ],
              ],
        ])}
      />
    </RACModalOverlay>
  );
}
