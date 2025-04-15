import React from 'react';
import {
  DateRangePicker as AriaDateRangePicker,
  DateRangePickerProps as AriaDateRangePickerProps,
  DateRangePickerStateContext,
  DateValue,
  useLocale,
  Group,
} from 'react-aria-components';
import { Button } from './button';
import { DateInput } from './date-field';
import { Dialog } from './dialog';
import { Popover } from './popover';
import { RangeCalendar } from './range-calendar';
import { composeTailwindRenderProps, inputField } from './utils';
import { twMerge } from 'tailwind-merge';
import { CalendarIcon } from './icons/outline/calendar';

export interface DateRangePickerProps<T extends DateValue>
  extends AriaDateRangePickerProps<T> {}

export function DateRangePicker<T extends DateValue>({
  ...props
}: DateRangePickerProps<T>) {
  return (
    <AriaDateRangePicker
      {...props}
      className={composeTailwindRenderProps(props.className, inputField)}
    />
  );
}

export function DateRangePickerInput() {
  return (
    <>
      <Group
        data-ui="control"
        className={({ isFocusWithin }) =>
          twMerge(
            'grid grid-cols-[max-content_16px_max-content_1fr] items-center',
            'group border-input relative rounded-md border',
            'group-data-invalid:border-red-600',
            '[&:has(_input[data-disabled=true])]:border-border/50',
            '[&:has([data-ui=date-segment][aria-readonly])]:bg-zinc-800/5',
            'dark:[&:has([data-ui=date-segment][aria-readonly])]:bg-white/10',
            isFocusWithin
              ? 'border-ring ring-ring group-data-invalid:border-ring ring-1'
              : '[&:has([data-ui=date-segment][aria-readonly])]:border-transparent',
          )
        }
      >
        <DateInput
          slot="start"
          className={[
            'flex min-w-fit border-none focus-within:ring-0',
            '[&:has([data-ui=date-segment][aria-readonly])]:bg-transparent',
            'dark:[&:has([data-ui=date-segment][aria-readonly])]:bg-transparent',
          ].join(' ')}
        />
        <span
          aria-hidden="true"
          className="text-muted place-self-center group-data-disabled:opacity-50"
        >
          –
        </span>
        <DateInput
          slot="end"
          className={[
            'flex min-w-fit border-none opacity-100 focus-within:ring-0',
            '[&:has([data-ui=date-segment][aria-readonly])]:bg-transparent',
            'dark:[&:has([data-ui=date-segment][aria-readonly])]:bg-transparent',
          ].join(' ')}
        />
        <Button
          variant="plain"
          isIconOnly
          size="sm"
          className="text-muted group-hover:text-foreground me-1 justify-self-end focus-visible:-outline-offset-1"
        >
          <CalendarIcon />
        </Button>
      </Group>
      <Popover placement="bottom" className="rounded-xl">
        <Dialog>
          <RangeCalendar />
        </Dialog>
      </Popover>
    </>
  );
}

export function DateRangePickerButton({
  className,
  children,
}: {
  className?: string;
  children?: React.ReactNode;
}) {
  const { locale } = useLocale();
  const state = React.useContext(DateRangePickerStateContext);
  const formattedValue = state?.formatValue(locale, {});

  return (
    <>
      <Group data-ui="control">
        <Button
          variant="outline"
          className={twMerge(
            'border-input w-full min-w-64 px-0 font-normal sm:px-0',
            className,
          )}
        >
          <div
            className={twMerge(
              'grid w-full items-center',
              formattedValue
                ? 'grid grid-cols-[1fr_16px_1fr_36px]'
                : 'grid-cols-[1fr_36px]',
            )}
          >
            {formattedValue ? (
              <>
                <span className="min-w-fit px-3 text-base/6 sm:text-sm/6">
                  {formattedValue.start}
                </span>
                <span
                  aria-hidden="true"
                  className="text-muted place-self-center group-data-disabled:opacity-50"
                >
                  –
                </span>
                <span className="min-w-fit px-3 text-base/6 sm:text-sm/6">
                  {formattedValue.end}
                </span>
              </>
            ) : (
              <span className="text-muted justify-self-start px-3">
                {children}
              </span>
            )}

            <CalendarIcon className="text-muted group-hover:text-foreground place-self-center" />
          </div>
        </Button>

        <DateInput slot="start" aria-hidden className="hidden" />
        <DateInput slot="end" aria-hidden className="hidden" />
      </Group>
      <Popover placement="bottom" className="rounded-xl">
        <Dialog>
          <RangeCalendar />
        </Dialog>
      </Popover>
    </>
  );
}
