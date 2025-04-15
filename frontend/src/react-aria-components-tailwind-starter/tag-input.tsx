import React from 'react';
import { LabelContext, TextFieldProps, type Key } from 'react-aria-components';
import { Tag, TagGroup, TagList } from './tag-group';
import { ListData } from 'react-stately';
import { Input, TextField } from './field';
import { twMerge } from 'tailwind-merge';

interface TagItem {
  id: number;
  name: string;
}

interface ContextType {
  list: ListData<TagItem>;
  onTagAdd?: (tag: TagItem) => void;
  onTagRemove?: (tag: TagItem) => void;
}

const TagInputContext = React.createContext<ContextType | null>(null);

function useTagInputContext() {
  const context = React.useContext(TagInputContext);

  if (!context) {
    throw new Error('<TagInputContext.Provider> is required');
  }

  return context;
}

export interface TagInputProps
  extends Omit<ContextType, 'tagGroupId'>,
    TextFieldProps {
  children: React.ReactNode;
  className?: string;
}

export function TagsInputField({
  list,
  name,
  onTagRemove,
  onTagAdd,
  ...props
}: TagInputProps) {
  return (
    <TagInputContext.Provider value={{ list, onTagAdd, onTagRemove }}>
      <TextField {...props} />
      {name && (
        <input
          name={name}
          hidden
          readOnly
          value={list.items.map(({ name }) => name).join(',')}
        />
      )}
    </TagInputContext.Provider>
  );
}

export function TagsInput({
  className,
}: {
  className?: string;
  children?: React.ReactNode;
}) {
  const [inputValue, setInputValue] = React.useState('');
  const { list, onTagAdd, onTagRemove } = useTagInputContext();

  const deleteLast = React.useCallback(() => {
    if (list.items.length == 0) {
      return;
    }

    const lastKey = list.items[list.items.length - 1];

    if (lastKey !== null) {
      list.remove(lastKey.id);
      const item = list.getItem(lastKey.id);

      if (item) {
        onTagRemove?.(item);
      }
    }
  }, [list, onTagRemove]);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ',' || e.key === ';') {
      e.preventDefault();
      addTag();
    }

    if (e.key === 'Backspace' && inputValue === '') {
      deleteLast();
    }
  }

  function addTag() {
    const tagNames = inputValue.split(/[,;]/);

    tagNames.forEach((tagName) => {
      const formattedName = tagName
        .trim()
        .replace(/\s\s+/g, ' ')
        .replace(/\t|\\t|\r|\\r|\n|\\n/g, '');

      if (formattedName === '') {
        return;
      }

      const hasTagExists = list.items.find(
        ({ name }) =>
          name.toLocaleLowerCase() === formattedName.toLocaleLowerCase(),
      );

      if (!hasTagExists) {
        const tag = {
          id: (list.items.at(-1)?.id || 0) + 1,
          name: formattedName,
        };

        list.append(tag);
        onTagAdd?.(tag);
      }
    });

    setInputValue('');
  }

  function handleRemove(keys: Set<Key>) {
    list.remove(...keys);
    const item = list.getItem([...keys][0]);

    if (item) {
      onTagRemove?.(item);
    }
  }

  const { id: labelId } = (React.useContext(LabelContext) ?? {}) as {
    id?: string;
  };

  return (
    <TagGroup
      aria-labelledby={labelId}
      onRemove={handleRemove}
      className={twMerge(className, 'w-full')}
      data-ui="control"
    >
      <div
        className={twMerge(
          'flex min-h-9 items-center rounded-md',
          'border has-[input[data-focused=true]]:border-ring',
          'has-[input[data-invalid=true][data-focused=true]]:border-ring has-[input[data-invalid=true]]:border-red-600',
          'has-[input[data-focused=true]]:ring-1 has-[input[data-focused=true]]:ring-ring',
        )}
      >
        <div className="inline-flex flex-1 flex-wrap items-center gap-1 px-2 py-[5px]">
          <TagList items={list.items} className="contents">
            {(item) => <Tag>{item.name}</Tag>}
          </TagList>

          <div className="flex flex-1">
            <Input
              value={inputValue}
              onChange={(e) => {
                setInputValue(e.target.value);
              }}
              onKeyDown={handleKeyDown}
              className="border-0 px-0.5 py-0 focus:ring-0 sm:py-0"
            />
          </div>
        </div>
      </div>
    </TagGroup>
  );
}
