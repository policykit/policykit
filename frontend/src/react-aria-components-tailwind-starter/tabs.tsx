import React from 'react';
import {
  Tab as RACTab,
  TabList as RACTabList,
  TabPanel as RACTabPanel,
  Tabs as RACTabs,
  TabListProps,
  TabPanelProps,
  TabProps,
  TabsProps as RACTabProps,
  composeRenderProps,
  TabRenderProps,
} from 'react-aria-components';
import { twMerge } from 'tailwind-merge';

type Orientation = 'vertical' | 'horizontal';
type Variant = 'underline' | 'pills' | 'segment';

const TabsContext = React.createContext<{
  variant: Variant;
  orientation: Orientation;
}>({
  variant: 'underline',
  orientation: 'horizontal',
});

export type TabsProps = RACTabProps &
  (
    | { variant?: 'underline' | 'pills' }
    | { variant: 'segment'; orientation?: never }
  );

export function Tabs({
  variant = 'underline',
  orientation = 'horizontal',
  keyboardActivation = 'manual',
  ...props
}: TabsProps) {
  return (
    <TabsContext.Provider value={{ variant, orientation }}>
      <RACTabs
        {...props}
        keyboardActivation={keyboardActivation}
        orientation={orientation}
        className={composeRenderProps(props.className, (className) =>
          twMerge([
            'group flex',
            orientation === 'horizontal' ? 'flex-col' : 'flex-col sm:flex-row',
            className,
          ]),
        )}
      />
    </TabsContext.Provider>
  );
}

const tabList = {
  base: {
    horizontal: 'whitespace-nowrap',
    vertical: 'flex-col flex-1 sm:flex-initial',
  },
  underline: {
    horizontal: 'w-full space-x-4 border-b',
    vertical: 'space-y-3.5 self-start border-l',
  },
  pills: {
    horizontal: 'space-x-4',
    vertical: 'space-y-2',
  },
  segment: {
    horizontal: 'p-0.5 rounded-lg bg-zinc-200/75 dark:bg-zinc-700 shadow-xs',
    vertical: '',
  },
};

export function TabList<T extends object>(props: TabListProps<T>) {
  const { variant, orientation } = React.useContext(TabsContext);

  return (
    <div className="flex overflow-x-auto pb-px pl-px">
      <RACTabList
        {...props}
        className={composeRenderProps(props.className, (className) =>
          twMerge([
            'flex',
            'text-base/6 sm:text-sm/6',
            tabList.base[orientation],
            tabList[variant][orientation],
            className,
          ]),
        )}
      />
    </div>
  );
}

const tabPanel = {
  underline: {
    horizontal: ['py-4'],
    vertical: ['px-4'],
  },
  pills: {
    horizontal: ['px-5 py-4'],
    vertical: ['p-4 sm:pl-8 sm:py-0'],
  },
  segment: {
    horizontal: ['px-3 py-4'],
    vertical: [],
  },
};

export function TabPanel(props: TabPanelProps) {
  const { variant, orientation } = React.useContext(TabsContext);

  return (
    <RACTabPanel
      {...props}
      className={composeRenderProps(props.className, (className) =>
        twMerge([
          'flex-1 outline-hidden',
          tabPanel[variant][orientation],
          className,
        ]),
      )}
    />
  );
}

const tab = ({
  isSelected,
  isDisabled,
  isHovered,
  isFocusVisible,
  variant,
  orientation,
}: {
  variant: Variant;
  orientation: Orientation;
} & TabRenderProps) => {
  const style = {
    base: [
      'outline-hidden relative flex items-center gap-x-3 rounded-md font-medium',
      '[&>[data-ui=icon]:not([class*=size-])]:size-5',
      isDisabled && 'opacity-50',
      isSelected || isHovered ? 'text-foreground' : 'text-muted',
      isFocusVisible && 'ring-2 ring-inset ring-ring',
    ],
    underline: {
      base: 'before:absolute before:bg-accent',
      horizontal: [
        'p-2 before:bottom-[-1.5px] before:w-full before:inset-x-0',
        isSelected && 'before:h-[2px]',
      ],
      vertical: [
        'px-4',
        'before:inset-y-0',
        isSelected && 'before:bg-accent before:left-[-1.5px] before:w-[2px]',
      ],
    },
    pills: {
      base: [
        'flex items-center px-3 py-2',
        isSelected && 'bg-zinc-100 dark:bg-zinc-600/45',
      ],
      horizontal: '',
      vertical: '',
    },
    segment: {
      base: [
        'flex-1 justify-center px-6 py-1 [&>[data-ui=icon]:not([class*=size-])]:size-4',
        isSelected &&
          'bg-background dark:bg-zinc-500 text-foreground shadow-2xs rounded-md',
      ],
      horizontal: '',
      vertical: '',
    },
  };

  return [style.base, style[variant].base, style[variant][orientation]];
};

export function Tab(props: TabProps) {
  const { variant, orientation } = React.useContext(TabsContext);

  return (
    <RACTab
      {...props}
      className={composeRenderProps(
        props.className,
        (className, renderProps) => {
          return twMerge(
            tab({
              variant,
              orientation,
              ...renderProps,
            }),
            className,
          );
        },
      )}
    />
  );
}
