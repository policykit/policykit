import React from 'react';
import {
  useFloating,
  autoUpdate,
  offset,
  flip,
  shift,
  useDismiss,
  useRole,
  useInteractions,
  FloatingFocusManager,
  useHover,
  safePolygon,
  Placement,
  ReferenceType,
} from '@floating-ui/react';
import { Heading, HeadingProps } from './heading';
import { twMerge } from 'tailwind-merge';

interface PopoverOptions {
  placement?: Placement;
  modal?: boolean;
}

function useHoverCard({ placement = 'bottom', modal }: PopoverOptions = {}) {
  const [isOpen, setIsOpen] = React.useState(false);
  const labelId = React.useId();

  const data = useFloating({
    placement,
    open: isOpen,
    onOpenChange: setIsOpen,
    middleware: [
      offset(10),
      flip({ fallbackAxisSideDirection: 'end' }),
      shift(),
    ],
    whileElementsMounted: autoUpdate,
  });

  const context = data.context;
  const dismiss = useDismiss(context);
  const role = useRole(context);
  const hover = useHover(context, {
    handleClose: safePolygon(),
    delay: 250,
  });

  const interactions = useInteractions([dismiss, role, hover]);

  return React.useMemo(
    () => ({
      isOpen,
      setIsOpen,
      ...interactions,
      ...data,
      modal,
      labelId,
    }),
    [isOpen, interactions, data, modal, labelId],
  );
}

type ContextType = ReturnType<typeof useHoverCard> | null;

const HoverCardContext = React.createContext<ContextType>(null);

const useHoverCardContext = () => {
  const context = React.useContext(HoverCardContext);

  if (context == null) {
    throw new Error('HoverCard components must be wrapped in <HoverCard />');
  }

  return context;
};

export function HoverCard({
  children,
  modal = false,
  ...restOptions
}: {
  children: React.ReactNode;
} & PopoverOptions) {
  const popover = useHoverCard({ modal, ...restOptions });

  return (
    <HoverCardContext.Provider value={popover}>
      {children}
    </HoverCardContext.Provider>
  );
}

export function HoverCardTrigger({ children }: { children: React.ReactNode }) {
  const context = useHoverCardContext();
  const child = React.Children.only(children);

  return React.cloneElement(
    child as React.ReactElement<{
      ref: ((node: ReferenceType | null) => void) &
        ((node: ReferenceType | null) => void);
    }>,
    {
      ref: context.refs.setReference,
      ...context.getReferenceProps(),
    },
  );
}

export function HoverCardContent({
  children,
  label,
  className,
}: {
  children:
    | React.ReactNode
    | (({ close }: { close: () => void }) => React.ReactNode);
} & {
  label?: string;
  className?: string;
}) {
  const {
    labelId,
    context: floatingContext,
    setIsOpen,
    isOpen,
    modal,
    refs,
    floatingStyles,
    getFloatingProps,
  } = useHoverCardContext();

  const aria = label ? { 'aria-label': label } : { 'aria-labelledby': labelId };

  return (
    isOpen && (
      <FloatingFocusManager context={floatingContext} modal={modal}>
        <div
          className={twMerge(
            'bg-background max-w-72 rounded-lg p-1 ring-1 shadow-lg ring-zinc-950/10 outline-hidden dark:bg-zinc-800 dark:ring-white/15',
            className,
          )}
          ref={refs.setFloating}
          style={floatingStyles}
          {...getFloatingProps()}
          {...aria}
        >
          {typeof children === 'function'
            ? children({ close: () => setIsOpen(false) })
            : children}
        </div>
      </FloatingFocusManager>
    )
  );
}

export function HoverCardHeader(props: HeadingProps) {
  const { labelId } = useHoverCardContext();
  return <Heading {...props} id={labelId}></Heading>;
}
