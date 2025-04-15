import {
  Cell as AriaCell,
  Column as AriaColumn,
  Row as AriaRow,
  Table as AriaTable,
  TableHeader as AriaTableHeader,
  Button,
  CellProps,
  Collection,
  ColumnProps,
  ColumnResizer,
  Group,
  ResizableTableContainer,
  RowProps,
  TableHeaderProps,
  TableProps,
  composeRenderProps,
  useTableOptions,
} from 'react-aria-components';
import { twMerge } from 'tailwind-merge';
import { Checkbox } from './checkbox';
import { composeTailwindRenderProps } from './utils';
import { ChevronUpIcon } from './icons/outline/chevron-up';

export function Table(props: TableProps) {
  return (
    <ResizableTableContainer className="relative max-h-[280px] w-[550px] scroll-pt-[2.281rem] overflow-auto rounded-md border">
      <AriaTable {...props} className="border-separate border-spacing-0" />
    </ResizableTableContainer>
  );
}

export function Column(props: ColumnProps) {
  return (
    <AriaColumn
      {...props}
      className={composeTailwindRenderProps(
        props.className,
        'cursor-default border-b text-start text-sm font-semibold focus-within:z-20 [&:hover]:z-20',
      )}
    >
      {composeRenderProps(
        props.children,
        (children, { allowsSorting, sortDirection }) => (
          <div className="flex items-center">
            <Group
              role="presentation"
              tabIndex={-1}
              className={composeRenderProps(
                '',
                (className, { isFocusVisible }) =>
                  twMerge(
                    isFocusVisible
                      ? 'outline-ring rounded-sm outline outline-2 outline-offset-2'
                      : 'outline-hidden',
                    'flex h-5 flex-1 items-center gap-1 overflow-hidden px-2',
                    className,
                  ),
              )}
            >
              <span className="truncate">{children}</span>
              {allowsSorting && (
                <span
                  className={`flex size-4 items-center justify-center transition ${
                    sortDirection === 'descending' ? 'rotate-180' : ''
                  }`}
                >
                  {sortDirection && (
                    <ChevronUpIcon className="size-4 text-muted" />
                  )}
                </span>
              )}
            </Group>
            {!props.width && (
              <ColumnResizer
                className={composeRenderProps(
                  '',
                  (className, { isFocusVisible, isResizing }) =>
                    twMerge(
                      'box-content h-5 w-[1.5px] translate-x-[8px] cursor-col-resize rounded-sm bg-border bg-clip-content px-[8px] py-1',
                      isResizing &&
                        'resizing:w-[2px] resizing:bg-accent resizing:pl-[7px]',
                      isFocusVisible
                        ? 'outline-ring rounded-sm outline outline-2 -outline-offset-2'
                        : 'outline-hidden',
                      className,
                    ),
                )}
              />
            )}
          </div>
        ),
      )}
    </AriaColumn>
  );
}

export function TableHeader<T extends object>(props: TableHeaderProps<T>) {
  const { selectionBehavior, selectionMode, allowsDragging } =
    useTableOptions();

  return (
    <AriaTableHeader
      {...props}
      className={composeTailwindRenderProps(props.className, [
        'sticky top-0 z-10 rounded-t-md  backdrop-blur-md',
        "after:content-['']",
        'after:flex-1',
      ])}
    >
      {/* Add extra columns for drag and drop and selection. */}
      {allowsDragging && <Column />}
      {selectionBehavior === 'toggle' && (
        <AriaColumn
          width={36}
          minWidth={36}
          className="cursor-default border-b p-2 text-start text-sm font-semibold"
        >
          {selectionMode === 'multiple' && <Checkbox slot="selection" />}
        </AriaColumn>
      )}
      <Collection items={props.columns}>{props.children}</Collection>
    </AriaTableHeader>
  );
}

export function Row<T extends object>({
  id,
  columns,
  children,
  ...props
}: RowProps<T>) {
  const { selectionBehavior, allowsDragging } = useTableOptions();

  return (
    <AriaRow
      id={id}
      {...props}
      className={composeRenderProps(
        props.className,
        (className, { isFocusVisible, isSelected, isHovered, isDisabled }) =>
          twMerge(
            'group/row relative cursor-default select-none text-sm',
            isDisabled && 'text-muted',
            isHovered && 'bg-zinc-100 dark:bg-zinc-700',
            isSelected && 'bg-accent/5 dark:bg-accent/35',
            isHovered && isSelected && 'bg-zinc-100 dark:selected:bg-zinc-700',
            isFocusVisible
              ? 'outline-ring rounded-sm outline outline-2 -outline-offset-2'
              : 'outline-hidden',
            className,
          ),
      )}
    >
      {allowsDragging && (
        <Cell>
          <Button slot="drag">≡</Button>
        </Cell>
      )}
      {selectionBehavior === 'toggle' && (
        <Cell>
          <Checkbox slot="selection" />
        </Cell>
      )}
      <Collection items={columns}>{children}</Collection>
    </AriaRow>
  );
}

export function Cell(props: CellProps) {
  return (
    <AriaCell
      {...props}
      className={composeRenderProps(
        props.className,
        (className, { isFocusVisible }) =>
          twMerge(
            'truncate border-b p-2 group-last/row:border-b-0',
            isFocusVisible
              ? 'outline-ring rounded-sm outline outline-2 -outline-offset-2'
              : 'outline-hidden',
            className,
          ),
      )}
    />
  );
}
