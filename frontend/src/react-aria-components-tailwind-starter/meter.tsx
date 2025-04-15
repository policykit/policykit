import {
  Meter as AriaMeter,
  MeterProps as AriaMeterProps,
} from 'react-aria-components';
import { Label } from './field';
import { composeTailwindRenderProps } from './utils';

export interface MeterProps extends AriaMeterProps {
  label?: string;
}

export function Meter({
  label,
  positive,
  informative,
  ...props
}: MeterProps &
  (
    | {
        positive?: true;
        informative?: never;
      }
    | { positive?: never; informative?: true }
  )) {
  return (
    <AriaMeter
      {...props}
      className={composeTailwindRenderProps(
        props.className,
        'flex flex-col gap-1',
      )}
    >
      {({ percentage, valueText }) => (
        <>
          <div className="flex justify-between gap-2">
            <Label>{label}</Label>
            <span
              className={`text-sm ${percentage >= 80 && !positive && !informative && 'text-red-600'}`}
            >
              {percentage >= 80 && !positive && (
                <svg
                  aria-label="Alert"
                  className="inline-block size-5 align-text-bottom"
                  xmlns="http://www.w3.org/2000/svg"
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3" />
                  <path d="M12 9v4" />
                  <path d="M12 17h.01" />
                </svg>
              )}
              {' ' + valueText}
            </span>
          </div>
          <div className="relative h-2 w-64  rounded-full bg-gray-300 outline outline-1 -outline-offset-1 outline-transparent dark:bg-zinc-800">
            <div
              className={`absolute left-0 top-0 h-full rounded-full ${getColor(percentage, { positive, informative })}`}
              style={{ width: percentage + '%' }}
            />
          </div>
        </>
      )}
    </AriaMeter>
  );
}

function getColor(
  percentage: number,
  { positive, informative }: { positive?: boolean; informative?: boolean },
) {
  if (positive) {
    return 'bg-success';
  }

  if (informative) {
    return 'bg-blue-500';
  }

  if (percentage < 70) {
    return 'bg-success';
  }

  if (percentage < 80) {
    return 'bg-yellow-600';
  }

  return 'bg-red-600';
}
