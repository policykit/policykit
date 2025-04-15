import {
  GridList as AriaGridList,
  GridListItem as AriaGridListItem,
  Button,
  composeRenderProps,
  GridListItemProps,
  GridListProps,
} from 'react-aria-components';
import { Checkbox } from './checkbox';
import { composeTailwindRenderProps} from './utils';
import { twMerge } from 'tailwind-merge';

export function GridList<T extends object>({
  children,
  ...props
}: GridListProps<T>) {
  return (
    <AriaGridList
      {...props}
      className={composeTailwindRenderProps(
        props.className,
        'relative overflow-auto rounded-md border p-1',
      )}
    >
      {children}
    </AriaGridList>
  );
}

export function GridListItem({ children, ...props }: GridListItemProps) {
  const textValue = typeof children === 'string' ? children : undefined;

  return (
    <AriaGridListItem
      {...props}
      textValue={textValue}
      className={composeRenderProps(
        props.className,
        (className, { isFocusVisible, isSelected, isDisabled, isHovered }) =>
          twMerge(
            'relative -mb-px flex cursor-default select-none gap-3 rounded-md px-2 py-1.5 text-sm outline-hidden',
            'not-last:mb-0.5',
            isHovered && ['bg-zinc100 dark:bg-zinc-800'],
            isSelected && ['z-20'],
            isDisabled && ['opacity-50'],
            isFocusVisible && [
              'outline',
              'outline-2',
              '-outline-offset-2',
              'outline-ring',
            ],

            className,
          ),
      )}
    >
      {(renderProps) =>
        typeof children === 'function' ? (
          children(renderProps)
        ) : (
          <>
            {/* Add elements for drag and drop and selection. */}
            {renderProps.allowsDragging && <Button slot="drag">≡</Button>}
            {renderProps.selectionMode === 'multiple' &&
              renderProps.selectionBehavior === 'toggle' && (
                <Checkbox slot="selection" />
              )}
            {children}
          </>
        )
      }
    </AriaGridListItem>
  );
}
