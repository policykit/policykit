import React from 'react';
import { Button, ButtonProps } from './button';
import { useCopyToClipboard } from './hooks/use-clipboard';
import { TooltipTrigger, Tooltip } from './tooltip';
import { CheckIcon } from './icons/outline/check';
import { CopyIcon } from './icons/outline/copy';
import { twMerge } from 'tailwind-merge';

export type ClipboardProps = {
  timeout?: number;
  children: (payload: {
    copied: boolean;
    copy: (value: string) => void;
  }) => React.ReactNode;
};

export function Clipboard({ timeout, children }: ClipboardProps) {
  const { copied, copy } = useCopyToClipboard({ timeout });
  return children({ copied, copy });
}

export function CopyButton({
  copyValue,
  label = 'Copy',
  labelAfterCopied = 'Copied to clipboard',
  icon,
  variant = 'plain',
  children,
  ...props
}: {
  copyValue: string;
  label?: string;
  labelAfterCopied?: string;
  icon?: React.JSX.Element;
} & Omit<ButtonProps, 'tooltip'>) {
  const [showTooltip, setShowTooltip] = React.useState(false);

  return (
    <Clipboard>
      {({ copied, copy }) => {
        return (
          <TooltipTrigger isOpen={copied || showTooltip}>
            <Button
              variant={variant}
              {...(!children && {
                isIconOnly: true,
              })}
              aria-label={label}
              {...props}
              onHoverChange={setShowTooltip}
              onPress={() => {
                copy(copyValue);
                setShowTooltip(false);
              }}
            >
              {children ?? (
                <>
                  {icon ? (
                    React.cloneElement(icon, {
                      className: twMerge(
                        'transition-all',
                        copied
                          ? 'absolute scale-0 opacity-0'
                          : 'scale-100 opacity-100',
                      ),
                    })
                  ) : (
                    <CopyIcon
                      className={twMerge(
                        'transition-all',
                        copied
                          ? 'absolute scale-0 opacity-0'
                          : 'scale-100 opacity-100',
                      )}
                    />
                  )}

                  <CheckIcon
                    className={twMerge(
                      'text-green-600 transition-all',
                      copied
                        ? 'scale-100 opacity-100'
                        : 'absolute scale-0 opacity-0',
                    )}
                  />
                </>
              )}
            </Button>
            <Tooltip>{copied ? labelAfterCopied : label}</Tooltip>
          </TooltipTrigger>
        );
      }}
    </Clipboard>
  );
}
