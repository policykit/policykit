import React from 'react';
import {
  DatePicker as RACDatePicker,
  DatePickerProps as RACDatePickerProps,
  DateValue,
  DatePickerStateContext,
  useLocale,
  Group,
  composeRenderProps,
} from 'react-aria-components';
import { Button } from './button';
import { Calendar, YearRange } from './calendar';
import { DateInput, DateInputProps } from './date-field';
import { Dialog } from './dialog';
import { Popover } from './popover';
import { inputField } from './utils';
import { twMerge } from 'tailwind-merge';
import { CalendarIcon } from './icons/outline/calendar';

export interface DatePickerProps<T extends DateValue>
  extends RACDatePickerProps<T> {}

export function DatePicker<T extends DateValue>(props: DatePickerProps<T>) {
  return (
    <RACDatePicker
      {...props}
      className={composeRenderProps(props.className, (className) => {
        return twMerge(inputField, className);
      })}
    />
  );
}

export function DatePickerInput({
  yearRange,
  ...props
}: DateInputProps & { yearRange?: YearRange }) {
  return (
    <>
      <Group
        data-ui="control"
        {...props}
        className={[
          'group',
          'grid w-auto min-w-52',
          'grid-cols-[1fr_calc(theme(size.5)+20px)]',
          'sm:grid-cols-[1fr_calc(theme(size.4)+20px)]',
        ].join(' ')}
      >
        <DateInput
          {...props}
          className={composeRenderProps(props.className, (className) =>
            twMerge(
              'col-span-full',
              'row-start-1',
              'sm:pe-9',
              'pe-10',
              className,
            ),
          )}
        />
        <Button
          variant="plain"
          size="sm"
          isIconOnly
          data-ui="trigger"
          className={[
            'focus-visible:-outline-offset-1',
            'row-start-1',
            '-col-end-1',
            'place-self-center',
            'text-muted group-hover:text-foreground',
          ].join(' ')}
        >
          <CalendarIcon />
        </Button>
      </Group>

      <Popover placement="bottom" className="rounded-xl">
        <Dialog>
          <Calendar yearRange={yearRange} />
        </Dialog>
      </Popover>
    </>
  );
}

export function DatePickerButton({
  className,
  children,
}: {
  className?: string;
  children?: React.ReactNode;
}) {
  const { locale } = useLocale();
  const state = React.useContext(DatePickerStateContext);
  const formattedDate = state?.formatValue(locale, {});

  return (
    <>
      <Group data-ui="control">
        <Button
          className={twMerge(
            'border-input w-full min-w-52 flex-1 justify-between px-3 leading-6 font-normal',
            className,
          )}
          variant="outline"
        >
          {formattedDate === '' ? (
            <span className="text-muted">{children}</span>
          ) : (
            <span>{formattedDate}</span>
          )}

          <CalendarIcon className="text-muted group-hover:text-foreground" />
        </Button>

        <DateInput className="hidden" aria-hidden />
      </Group>

      <Popover placement="bottom" className="rounded-xl">
        <Dialog>
          <Calendar />
        </Dialog>
      </Popover>
    </>
  );
}
