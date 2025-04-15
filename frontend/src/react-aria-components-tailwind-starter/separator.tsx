import { useSeparator } from 'react-aria';
import { twMerge } from 'tailwind-merge';
import { SeparatorProps as RACSeparatorProps } from 'react-aria-components';

export type SeparatorProps = RACSeparatorProps & {
  children?: React.ReactNode;
  soft?: boolean;
} & React.JSX.IntrinsicElements['div'];

export function Separator({
  orientation = 'horizontal',
  className,
  soft = false,
  children,
  ...props
}: SeparatorProps) {
  const { separatorProps } = useSeparator({ orientation });

  return (
    <div
      {...separatorProps}
      className={twMerge(
        'text-sm/6',
        '[&>svg:not([class*=size])]:size-5',
        children
          ? [
              soft
                ? 'before:border-border/50 after:border-border/50'
                : 'before:border-border after:border-border',
              orientation === 'vertical'
                ? [
                    'mx-4 flex flex-col items-center',
                    "before:content-['']",
                    'before:border-l',
                    'before:flex-1',
                    "after:content-['']",
                    'after:border-r',
                    'after:flex-1',
                    typeof children === 'string' && ['before:mb-4 after:mt-4'],
                  ]
                : [
                    'self-stretch',
                    'my-2 flex items-center',
                    "before:content-['']",
                    'before:border-t',
                    'before:flex-1',

                    "after:content-['']",
                    'after:border-t',
                    'after:flex-1',
                    typeof children === 'string' && ['before:me-4 after:ms-4'],
                  ],
            ]
          : [
              soft ? 'border-border/50' : 'border-border',
              orientation === 'vertical'
                ? [
                    'h-auto self-stretch border-l',
                    typeof children === 'string' && ['mx-1'],
                  ]
                : [
                    'h-px w-full self-stretch border-b',
                    typeof children === 'string' && ['my-1'],
                  ],
            ],
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}
