import React, { useState } from 'react';
import {
  ComboBox,
  ComboBoxProps as RACComboBoxProps,
  Key,
  ListBoxItemProps,
  composeRenderProps,
  GroupProps,
  LabelContext,
  Group,
} from 'react-aria-components';
import { useListData, ListData } from 'react-stately';
import { useFilter } from 'react-aria';
import {
  DescriptionProvider,
  LabeledGroup,
  Input,
  DescriptionContext,
} from './field';
import { Popover } from './popover';
import { ListBox, ListBoxItem } from './list-box';
import { Button } from './button';
import { twMerge } from 'tailwind-merge';
import { TagGroup, TagList } from './tag-group';
import { composeTailwindRenderProps, inputField } from './utils';

export interface MultiSelectProps<T extends object>
  extends Omit<
    RACComboBoxProps<T>,
    | 'children'
    | 'validate'
    | 'allowsEmptyCollection'
    | 'inputValue'
    | 'selectedKey'
    | 'inputValue'
    | 'className'
    | 'value'
    | 'onSelectionChange'
    | 'onInputChange'
  > {
  items: Array<T>;
  selectedList: ListData<T>;
  className?: string;
  onItemAdd?: (key: Key) => void;
  onItemRemove?: (key: Key) => void;
  renderEmptyState: (inputValue: string) => React.ReactNode;
  tag: (item: T) => React.ReactNode;
  children: React.ReactNode | ((item: T) => React.ReactNode);
}

export function MultiSelectField({
  children,
  className,
  ...props
}: GroupProps & { children: React.ReactNode }) {
  return (
    <LabeledGroup {...props}>
      <Group className={composeTailwindRenderProps(className, inputField)}>
        <DescriptionProvider>{children}</DescriptionProvider>
      </Group>
    </LabeledGroup>
  );
}

export function MultiSelect<
  T extends {
    id: Key;
    textValue: string;
  },
>({
  children,
  items,
  selectedList,
  onItemRemove,
  onItemAdd,
  className,
  name,
  renderEmptyState,
  ...props
}: MultiSelectProps<T>) {
  const { contains } = useFilter({ sensitivity: 'base' });

  const selectedKeys = selectedList.items.map((i) => i.id);

  const filter = React.useCallback(
    (item: T, filterText: string) => {
      return (
        !selectedKeys.includes(item.id) && contains(item.textValue, filterText)
      );
    },
    [contains, selectedKeys],
  );

  const availableList = useListData({
    initialItems: items,
    filter,
  });

  const [fieldState, setFieldState] = useState<{
    selectedKey: Key | null;
    inputValue: string;
  }>({
    selectedKey: null,
    inputValue: '',
  });

  const onRemove = React.useCallback(
    (keys: Set<Key>) => {
      const key = keys.values().next().value;
      if (key) {
        selectedList.remove(key);
        setFieldState({
          inputValue: '',
          selectedKey: null,
        });
        onItemRemove?.(key);
      }
    },
    [selectedList, onItemRemove],
  );

  const onSelectionChange = (id: Key | null) => {
    if (!id) {
      return;
    }

    const item = availableList.getItem(id);

    if (!item) {
      return;
    }

    if (!selectedKeys.includes(id)) {
      selectedList.append(item);
      setFieldState({
        inputValue: '',
        selectedKey: id,
      });
      onItemAdd?.(id);
    }

    availableList.setFilterText('');
  };

  const onInputChange = (value: string) => {
    setFieldState((prevState) => ({
      inputValue: value,
      selectedKey: value === '' ? null : prevState.selectedKey,
    }));

    availableList.setFilterText(value);
  };

  const deleteLast = React.useCallback(() => {
    if (selectedList.items.length == 0) {
      return;
    }

    const lastKey = selectedList.items[selectedList.items.length - 1];

    if (lastKey !== null) {
      selectedList.remove(lastKey.id);
      onItemRemove?.(lastKey.id);
    }

    setFieldState({
      inputValue: '',
      selectedKey: null,
    });
  }, [selectedList, onItemRemove]);

  const onKeyDownCapture = React.useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Backspace' && fieldState.inputValue === '') {
        deleteLast();
      }
    },
    [deleteLast, fieldState.inputValue],
  );

  const tagGroupId = React.useId();
  const triggerRef = React.useRef<HTMLDivElement | null>(null);

  const [width, setWidth] = React.useState(0);

  React.useEffect(() => {
    const trigger = triggerRef.current;
    if (!trigger) {
      return;
    }

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setWidth(entry.target.clientWidth);
      }
    });

    observer.observe(trigger);
    return () => {
      observer.unobserve(trigger);
    };
  }, [triggerRef]);

  const triggerButtonRef = React.useRef<HTMLButtonElement | null>(null);

  const labelContext = (React.useContext(LabelContext) ?? {}) as {
    id?: string;
  };
  const descriptionContext = React.useContext(DescriptionContext);

  return (
    <>
      <div
        data-ui="control"
        ref={triggerRef}
        className={twMerge(
          'relative',
          'pe-4',
          'flex min-h-9 w-[350px] flex-row flex-wrap items-center rounded-md',
          'border has-[input[data-focused=true]]:border-ring',
          'has-[input[data-invalid=true][data-focused=true]]:border-ring has-[input[data-invalid=true]]:border-red-600',
          'has-[input[data-focused=true]]:ring-1 has-[input[data-focused=true]]:ring-ring',
          className,
        )}
      >
        {selectedList.items.length > 0 && (
          <TagGroup
            id={tagGroupId}
            aria-labelledby={labelContext.id}
            className="contents"
            onRemove={onRemove}
          >
            <TagList
              items={selectedList.items}
              className={twMerge(
                selectedList.items.length !== 0 && 'p-1',
                'outline-hidden',
              )}
            >
              {props.tag}
            </TagList>
          </TagGroup>
        )}

        <ComboBox
          {...props}
          allowsEmptyCollection
          className={twMerge('group flex flex-1', className)}
          items={availableList.items}
          selectedKey={fieldState.selectedKey}
          inputValue={fieldState.inputValue}
          onSelectionChange={onSelectionChange}
          onInputChange={onInputChange}
          aria-labelledby={labelContext.id}
        >
          <div
            className={[
              'inline-flex flex-1 flex-wrap items-center gap-1 px-2',
              selectedList.items.length > 0 && 'ps-0',
            ].join(' ')}
          >
            <Input
              className="me-4 flex-1 border-0 px-0.5 py-0 outline-0 focus:ring-0"
              onBlur={() => {
                setFieldState({
                  inputValue: '',
                  selectedKey: null,
                });
                availableList.setFilterText('');
              }}
              aria-describedby={[
                tagGroupId,
                descriptionContext?.['aria-describedby'] ?? '',
              ].join(' ')}
              onKeyDownCapture={onKeyDownCapture}
            />

            <div className="sr-only" aria-hidden>
              <Button variant="plain" ref={triggerButtonRef}>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="size-4"
                >
                  <path d="m6 9 6 6 6-6" />
                </svg>
              </Button>
            </div>
          </div>
          <Popover
            style={{ width: `${width}px` }}
            triggerRef={triggerRef}
            className="max-w-none duration-0"
          >
            <ListBox<T>
              renderEmptyState={() => renderEmptyState(fieldState.inputValue)}
              selectionMode="multiple"
              className="flex max-h-[inherit] flex-col gap-1.5 overflow-auto p-1.5 outline-hidden has-[header]:pt-0 sm:gap-0"
            >
              {children}
            </ListBox>
          </Popover>
        </ComboBox>
        <Button variant="plain" asChild>
          <div
            className="top-50 absolute end-0 me-1 size-6 rounded-sm p-0.5"
            aria-hidden
          >
            {/* React Aria Button does not allow tabIndex */}
            <button
              type="button"
              onClick={() => triggerButtonRef.current?.click()}
              tabIndex={-1}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="size-4 text-muted group-hover:text-foreground"
              >
                <path d="m6 9 6 6 6-6" />
              </svg>
            </button>
          </div>
        </Button>
      </div>

      {name && (
        <input hidden name={name} value={selectedKeys.join(',')} readOnly />
      )}
    </>
  );
}

export function MultiSelectItem(props: ListBoxItemProps) {
  return (
    <ListBoxItem
      {...props}
      className={composeRenderProps(
        props.className,
        (className, { isFocused }) => {
          return twMerge([
            'rounded-md p-1.5 text-base/6 outline-0 focus-visible:outline-0 sm:text-sm/6',
            isFocused && 'bg-zinc-100 dark:bg-zinc-700',
            className,
          ]);
        },
      )}
    >
      {props.children}
    </ListBoxItem>
  );
}
