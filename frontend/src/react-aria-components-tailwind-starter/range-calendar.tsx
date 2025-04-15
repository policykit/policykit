import {
  RangeCalendar as RACRangeCalendar,
  RangeCalendarProps as RACRangeCalendarProps,
  CalendarCell,
  CalendarGrid,
  CalendarGridBody,
  DateValue,
  Text,
  composeRenderProps,
} from 'react-aria-components';
import { CalendarGridHeader, CalendarHeader } from './calendar';
import { twMerge } from 'tailwind-merge';
import { getLocalTimeZone, isToday } from '@internationalized/date';

export interface RangeCalendarProps<T extends DateValue>
  extends Omit<RACRangeCalendarProps<T>, 'visibleDuration'> {
  errorMessage?: string;
}

export function RangeCalendar<T extends DateValue>({
  errorMessage,
  ...props
}: RangeCalendarProps<T>) {
  return (
    <RACRangeCalendar
      {...props}
      className={composeRenderProps(props.className, (className) => {
        return twMerge('px-1.5 py-2.5', className);
      })}
    >
      <CalendarHeader />
      <CalendarGrid className="border-separate border-spacing-y-1 px-3 sm:px-2">
        <CalendarGridHeader />
        <CalendarGridBody>
          {(date) => (
            <CalendarCell
              date={date}
              className={composeRenderProps(
                '',
                (
                  className,
                  { isSelected, isSelectionStart, isSelectionEnd, isInvalid },
                ) => {
                  return twMerge(
                    'group grid size-10 cursor-default place-items-center text-sm outline-hidden [td:first-child_&]:rounded-s-lg [td:last-child_&]:rounded-e-lg',
                    isToday(date, getLocalTimeZone()) && [
                      isSelected
                        ? 'rounded-none'
                        : 'rounded-lg bg-zinc-100 dark:bg-zinc-800',
                    ],
                    isSelected &&
                      'bg-accent/[0.07] dark:bg-accent/35 dark:text-white',
                    isSelected &&
                      isInvalid &&
                      'bg-red-600/15 text-red-600 dark:bg-red-600/30',
                    isSelectionStart && 'rounded-s-lg',
                    isSelectionEnd && 'rounded-e-lg',
                    className,
                  );
                },
              )}
            >
              {({
                formattedDate,
                isSelected,
                isInvalid,
                isHovered,
                isPressed,
                isSelectionStart,
                isSelectionEnd,
                isFocusVisible,
                isUnavailable,
                isDisabled,
              }) => (
                <span
                  className={twMerge(
                    'relative flex size-[calc(--spacing(10)-1px)] items-center justify-center',
                    isHovered && [
                      'rounded-lg bg-zinc-100 dark:bg-zinc-700',
                      isPressed && 'bg-accent/90',
                      isSelected &&
                        'bg-accent dark:bg-accent text-[lch(from_var(--color-accent)_calc((49.44_-_l)_*_infinity)_0_0)]',
                    ],
                    isDisabled && 'opacity-50',
                    isUnavailable &&
                      'text-red-600 line-through decoration-red-600',
                    (isSelectionStart || isSelectionEnd) && [
                      'bg-accent rounded-lg text-sm text-[lch(from_var(--color-accent)_calc((49.44_-_l)_*_infinity)_0_0)]',
                      isHovered && 'bg-accent/90 dark:bg-accent/90',
                      isInvalid && 'border-red-600 bg-red-600 text-white',
                    ],
                    isFocusVisible && [
                      'outline-ring outline outline-2',
                      (isSelectionStart || isSelectionEnd) &&
                        'outline-offset-1',
                      'rounded-lg',
                    ],
                  )}
                >
                  {formattedDate}
                </span>
              )}
            </CalendarCell>
          )}
        </CalendarGridBody>
      </CalendarGrid>
      {errorMessage && (
        <Text slot="errorMessage" className="text-sm text-red-600">
          {errorMessage}
        </Text>
      )}
    </RACRangeCalendar>
  );
}
