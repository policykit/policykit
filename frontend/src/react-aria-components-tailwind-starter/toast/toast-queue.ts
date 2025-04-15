import { ToastAria } from '@react-aria/toast';
import { ToastQueue } from '@react-stately/toast';

type Position =
  | 'top-left'
  | 'top-center'
  | 'top-right'
  | 'bottom-left'
  | 'bottom-center'
  | 'bottom-right';

type Type = 'info' | 'error' | 'success' | 'warning';

export type ToastConfig =
  | {
      position?: Position;
      title?: React.ReactNode;
      description?: React.ReactNode;
      action?: React.ReactNode;
      compact?: boolean;
      inline?: boolean;
      dismissable?: boolean;
      render?: never;
      type?: Type;
    }
  | {
      render: (toast: ToastAria) => React.ReactNode;
      position?: Position;
      type?: Type;
    };

export const toast = new ToastQueue<ToastConfig>({
  maxVisibleToasts: 5,
});
