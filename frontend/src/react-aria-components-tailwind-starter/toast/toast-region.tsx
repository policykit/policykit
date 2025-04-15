import React from 'react';
import { createPortal } from 'react-dom';
import { useToastQueue } from '@react-stately/toast';
import type { AriaToastRegionProps, ToastAria } from '@react-aria/toast';
import type { ToastState } from '@react-stately/toast';
import { useToastRegion } from '@react-aria/toast';
import type { AriaToastProps } from '@react-aria/toast';
import { useToast } from '@react-aria/toast';
import { ButtonProps as AriaButtonProps } from 'react-aria-components';
import { twMerge } from 'tailwind-merge';
import { toast, ToastConfig } from './toast-queue';
import Callout, {
  CalloutActions,
  CalloutColor,
  CalloutControl,
  CalloutDescription,
  CalloutHeading,
} from '../callout';
import { InformationCircleIcon } from '../icons/solid/information-circle';
import { XCircleIcon } from '../icons/solid/x-circle';
import { ExclamationCircleIcon } from '../icons/solid/exclamation-circle';
import { CheckCircleIcon } from '../icons/solid/check-circle';

interface ToastRegionProps extends AriaToastRegionProps {
  state: ToastState<ToastConfig>;
}

interface ToastProps extends AriaToastProps<ToastConfig> {
  state: ToastState<ToastConfig>;
}

function ToastRegion({ state, ...props }: ToastRegionProps) {
  const ref = React.useRef(null);
  const { regionProps } = useToastRegion(props, state, ref);

  const position = state.visibleToasts[0].content.position ?? 'bottom-right';

  let className = 'bottom-6 right-6';
  switch (position) {
    case 'bottom-left':
      className = 'bottom-6 left-6';
      break;
    case 'bottom-center':
      className = 'bottom-6 left-1/2 -translate-x-1/2';
      break;
    case 'top-left':
      className = 'top-6 left-6 ';
      break;
    case 'top-center':
      className = 'top-6 left-1/2 -translate-x-1/2';
      break;
    case 'top-right':
      className = 'top-6 right-6';
      break;
    default:
      break;
  }

  return (
    <div
      {...regionProps}
      data-position={position}
      ref={ref}
      className={twMerge(
        'group toast-region fixed isolate z-20 flex flex-col gap-2 outline-hidden',
        className,
      )}
    >
      {state.visibleToasts.map((toast) => {
        return <Toast key={toast.key} toast={toast} state={state} />;
      })}
    </div>
  );
}

export function GlobalToastRegion(props: AriaToastRegionProps) {
  const state = useToastQueue<ToastConfig>(toast);

  return state.visibleToasts.length > 0
    ? createPortal(<ToastRegion {...props} state={state} />, document.body)
    : null;
}

function Toast({ state, ...props }: ToastProps) {
  const ref = React.useRef(null);
  const toast: Omit<ToastAria, 'closeButtonProps'> & {
    closeButtonProps: Omit<AriaButtonProps, 'children'>;
  } = useToast(props, state, ref);

  const type = props.toast.content.type;

  let color: CalloutColor;

  switch (type) {
    case 'info':
      color = 'blue';
      break;
    case 'success':
      color = 'green';
      break;
    case 'warning':
      color = 'yellow';
      break;
    case 'error':
      color = 'red';
      break;
    default:
      color = 'zinc';
      break;
  }

  return (
    <div
      {...toast.toastProps}
      ref={ref}
      className={twMerge(
        'relative isolate flex',
        'group-data-[position=top-left]:w-[min(85vw,360px)]',
        'group-data-[position=top-right]:w-[min(85vw,360px)]',
        'group-data-[position=bottom-left]:w-[min(85vw,360px)]',
        'group-data-[position=bottom-right]:w-[min(85vw,360px)]',
      )}
    >
      {props.toast.content.render ? (
        props.toast.content.render(toast)
      ) : (
        <>
          <Callout
            role={null}
            color={color}
            compact={props.toast.content.compact}
            inline={props.toast.content.inline}
          >
            {props.toast.content.dismissable !== false && (
              <CalloutControl slot="close" {...toast.closeButtonProps} />
            )}
            {props.toast.content.title ? (
              <CalloutHeading {...toast.titleProps}>
                {type === 'info' && <InformationCircleIcon />}
                {type === 'error' && <XCircleIcon />}
                {type === 'warning' && <ExclamationCircleIcon />}
                {type === 'success' && <CheckCircleIcon />}
                {props.toast.content.title}
              </CalloutHeading>
            ) : null}
            {props.toast.content.description ? (
              <CalloutDescription elementType="div" {...toast.descriptionProps}>
                {props.toast.content.description}
              </CalloutDescription>
            ) : null}
            {props.toast.content.action ? (
              <CalloutActions>{props.toast.content.action}</CalloutActions>
            ) : null}
          </Callout>
        </>
      )}
    </div>
  );
}
