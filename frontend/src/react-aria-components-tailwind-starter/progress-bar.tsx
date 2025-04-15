import {
  ProgressBar as AriaProgressBar,
  ProgressBarProps as AriaProgressBarProps,
} from 'react-aria-components';
import { Label } from './field';
import { composeTailwindRenderProps } from './utils';

export interface ProgressBarProps extends AriaProgressBarProps {
  label?: string;
}

export function ProgressBar({ label, ...props }: ProgressBarProps) {
  return (
    <AriaProgressBar
      {...props}
      className={composeTailwindRenderProps(
        props.className,
        'flex flex-col gap-1',
      )}
    >
      {({ percentage, valueText, isIndeterminate }) => (
        <>
          <div className="flex justify-between gap-2">
            <Label>{label}</Label>
            <span className="text-sm text-muted">{valueText}</span>
          </div>
          <div className="relative h-2 w-64 overflow-hidden rounded-full bg-gray-300 outline outline-1 -outline-offset-1 outline-transparent dark:bg-zinc-700">
            <div
              className={`absolute top-0 h-full rounded-full bg-accent  ${isIndeterminate ? 'left-full duration-1000 ease-out animate-in slide-in-from-left-[20rem] repeat-infinite' : 'left-0'}`}
              style={{ width: (isIndeterminate ? 40 : percentage) + '%' }}
            />
          </div>
        </>
      )}
    </AriaProgressBar>
  );
}
