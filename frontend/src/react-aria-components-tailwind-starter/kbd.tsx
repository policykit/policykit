import { Keyboard as RACKeyboard } from 'react-aria-components';
import { twMerge } from 'tailwind-merge';

export type KeyboardProps = Omit<
  React.JSX.IntrinsicElements['div'],
  'children'
> & {
  children: string;
  outline?: boolean;
};

export function Kbd({ className, children, outline, ...props }: KeyboardProps) {
  return (
    <RACKeyboard
      {...props}
      data-ui="kbd"
      className={twMerge(
        'font-sans text-base/6 tracking-widest sm:text-sm/6',
        outline &&
          'rounded-sm bg-zinc-200 px-1 py-0.5 font-medium dark:bg-white/10',
        className,
      )}
    >
      {children}
    </RACKeyboard>
  );
}
