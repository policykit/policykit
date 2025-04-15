import React from 'react';
import {
  Heading,
  Calendar as RACCalendar,
  CalendarGridHeader as RACCalendarGridHeader,
  CalendarProps as RACCalendarProps,
  CalendarCell,
  CalendarGrid,
  CalendarGridBody,
  CalendarHeaderCell,
  DateValue,
  Text,
  useLocale,
  composeRenderProps,
  CalendarStateContext,
} from 'react-aria-components';
import { Button, ButtonGroup } from './button';
import { twMerge } from 'tailwind-merge';
import { ChevronLeftIcon } from './icons/outline/chevron-left';
import { ChevronRightIcon } from './icons/outline/chevron-right';
import {
  CalendarDate,
  getLocalTimeZone,
  isToday,
} from '@internationalized/date';
import { CalendarState } from '@react-stately/calendar';
import { useDateFormatter } from '@react-aria/i18n';
import { NativeSelect, NativeSelectField } from './native-select';
import { Label } from './field';

export type YearRange = number | [yearsBefore: number, yearsAfter: number];

export interface CalendarProps<T extends DateValue>
  extends Omit<RACCalendarProps<T>, 'visibleDuration'> {
  yearRange?: YearRange;
  errorMessage?: string;
}

export function Calendar<T extends DateValue>({
  errorMessage,
  yearRange,
  ...props
}: CalendarProps<T>) {
  return (
    <RACCalendar
      {...props}
      className={composeRenderProps(props.className, (className) => {
        return twMerge('px-1 py-2.5', className);
      })}
    >
      <CalendarHeader yearRange={yearRange} />
      <CalendarGrid
        className="w-full border-separate border-spacing-y-1 px-2"
      >
        <CalendarGridHeader />
        <CalendarGridBody>
          {(date) => {
            return (
              <CalendarCell
                date={date}
                className={composeRenderProps(
                  '',
                  (
                    className,
                    {
                      isHovered,
                      isPressed,
                      isDisabled,
                      isSelected,
                      isInvalid,
                      isUnavailable,
                      isFocusVisible,
                    },
                  ) => {
                    return twMerge(
                      'relative flex size-10 cursor-default items-center justify-center rounded-lg text-sm outline-hidden',
                      isToday(date, getLocalTimeZone()) &&
                        'bg-zinc-100 dark:bg-zinc-800',
                      isHovered && 'bg-zinc-100 dark:bg-zinc-800',
                      isPressed && 'bg-accent/90 text-white',
                      isDisabled && 'opacity-50',
                      isSelected && [
                        'bg-accent text-sm text-[lch(from_var(--color-accent)_calc((49.44_-_l)_*_infinity)_0_0)]',
                        isHovered && 'bg-accent dark:bg-accent',
                        isInvalid && 'border-red-600 bg-red-600 text-white',
                      ],
                      isUnavailable &&
                        'text-red-600 line-through decoration-red-600',
                      isFocusVisible && [
                        'outline-ring outline outline-2',
                        isSelected && 'outline-offset-1',
                      ],
                      className,
                    );
                  },
                )}
              />
            );
          }}
        </CalendarGridBody>
      </CalendarGrid>
      {errorMessage && (
        <Text slot="errorMessage" className="text-sm text-red-600">
          {errorMessage}
        </Text>
      )}
    </RACCalendar>
  );
}

// https://github.com/adobe/react-spectrum/discussions/3950#discussioncomment-4851719
export function CalendarHeader({ yearRange }: { yearRange?: YearRange }) {
  const { direction } = useLocale();
  const state = React.use(CalendarStateContext)!;

  return (
    <header
      className={twMerge(
        'flex w-full items-center py-1 ps-4 pe-2',
        yearRange ? 'ps-2' : 'ps-4',
      )}
    >
      {yearRange ? (
        <div className="flex flex-1 gap-x-2 text-center text-left text-base/6 sm:text-sm/6 rtl:text-right">
          <MonthDropdown state={state} />
          <YearDropdown state={state} yearRange={yearRange} />
        </div>
      ) : (
        <Heading
          level={2}
          className="flex flex-1 text-center text-left text-base/6 font-medium sm:text-sm/6 rtl:text-right"
          aria-hidden
        ></Heading>
      )}

      <ButtonGroup>
        <Button
          slot="previous"
          variant="plain"
          size="sm"
          isIconOnly
          aria-label="Previous"
          className="[&:not(:hover)]:text-muted/75 focus-visible:-outline-offset-2"
        >
          {direction === 'rtl' ? (
            <ChevronRightIcon className="sm:size-5" />
          ) : (
            <ChevronLeftIcon className="sm:size-5" />
          )}
        </Button>

        <Button
          size="sm"
          slot="next"
          variant="plain"
          isIconOnly
          aria-label="Next"
          className="[&:not(:hover)]:text-muted/75 focus-visible:-outline-offset-2"
        >
          {direction === 'rtl' ? (
            <ChevronLeftIcon className="sm:size-5" />
          ) : (
            <ChevronRightIcon className="sm:size-5" />
          )}
        </Button>
      </ButtonGroup>
    </header>
  );
}

export function CalendarGridHeader() {
  return (
    <RACCalendarGridHeader>
      {(day) => (
        <CalendarHeaderCell className="text-muted size-10 text-sm/6 font-normal">
          {day}
        </CalendarHeaderCell>
      )}
    </RACCalendarGridHeader>
  );
}

function YearDropdown({
  state,
  yearRange,
}: {
  state: CalendarState;
  yearRange: YearRange;
}) {
  const years: Array<{
    value: CalendarDate;
    formatted: string;
  }> = [];
  const formatter = useDateFormatter({
    year: 'numeric',
    timeZone: state.timeZone,
  });

  const [yearsBefore, yearsAfter] = Array.isArray(yearRange)
    ? yearRange
    : [yearRange, yearRange];

  if (yearsBefore <= 0 || yearsAfter <= 0) {
    throw new Error(
      'The yearRange prop must be a positive number or an array of two positive numbers.',
    );
  }

  for (let i = yearsBefore * -1; i <= yearsAfter; i++) {
    const date = state.focusedDate.add({ years: i });
    years.push({
      value: date,
      formatted: formatter.format(date.toDate(state.timeZone)),
    });
  }

  const onChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const index = Number(e.target.value);
    const date = years[index].value;
    state.setFocusedDate(date);
  };

  return (
    <NativeSelectField>
      <Label className="sr-only">Year</Label>
      <NativeSelect onChange={onChange} value={yearsBefore}>
        {years.map((year, i) => (
          // use the index as the value so we can retrieve the full
          // date object from the list in onChange. We cannot only
          // store the year number, because in some calendars, such
          // as the Japanese, the era may also change.
          <option key={i} value={i}>
            {year.formatted}
          </option>
        ))}
      </NativeSelect>
    </NativeSelectField>
  );
}

function MonthDropdown({ state }: { state: CalendarState }) {
  const months: Array<string> = [];
  const formatter = useDateFormatter({
    month: 'long',
    timeZone: state.timeZone,
  });

  // Format the name of each month in the year according to the
  // current locale and calendar system. Note that in some calendar
  // systems, such as the Hebrew, the number of months may differ
  // between years.
  const numMonths = state.focusedDate.calendar.getMonthsInYear(
    state.focusedDate,
  );
  for (let i = 1; i <= numMonths; i++) {
    const date = state.focusedDate.set({ month: i });
    months.push(formatter.format(date.toDate(state.timeZone)));
  }

  const onChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = Number(e.target.value);
    const date = state.focusedDate.set({ month: value });
    state.setFocusedDate(date);
  };

  return (
    <NativeSelectField>
      <Label className="sr-only">Month</Label>
      <NativeSelect onChange={onChange} value={state.focusedDate.month}>
        {months.map((month, i) => (
          <option key={i} value={i + 1}>
            {month}
          </option>
        ))}
      </NativeSelect>
    </NativeSelectField>
  );
}
