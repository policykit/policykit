import React from 'react';
import {
  composeRenderProps,
  Radio as RACRadio,
  RadioGroup as RACRadioGroup,
  RadioGroupProps as RACRadioGroupProps,
  RadioProps as RACRadioProps,
  RadioRenderProps,
} from 'react-aria-components';
import { twMerge } from 'tailwind-merge';
import { DescriptionContext, DescriptionProvider } from './field';
import { composeTailwindRenderProps, groupBox } from './utils';

export function RadioGroup(props: RACRadioGroupProps) {
  return (
    <RACRadioGroup
      {...props}
      className={composeTailwindRenderProps(props.className, groupBox)}
    />
  );
}

export function Radios({
  className,
  ...props
}: React.JSX.IntrinsicElements['div']) {
  return (
    <div
      data-ui="box"
      className={twMerge(
        'flex',
        'flex-col',
        'group-aria-[orientation=horizontal]:flex-row',
        'group-aria-[orientation=horizontal]:flex-wrap',
        // When any radio item has description, apply all `font-medium` to all radio item labels
        'has-data-[ui=description]:[&_label]:font-medium',
        className,
      )}
      {...props}
    />
  );
}

export function RadioField({
  className,
  ...props
}: React.JSX.IntrinsicElements['div']) {
  return (
    <DescriptionProvider>
      <div
        {...props}
        data-ui="field"
        className={twMerge(
          'group flex flex-col gap-y-1',
          'has-data-[label-placement=start]:[&_label]:justify-between',
          'has-[label[data-label-placement=start]]:[&_[data-ui=description]:not([class*=pe-])]:pe-16',
          'has-[label[data-label-placement=end]]:[&_[data-ui=description]:not([class*=ps-])]:ps-7',
          'has-[label[data-disabled]]:**:data-[ui=description]:opacity-50',
          className,
        )}
      />
    </DescriptionProvider>
  );
}

export interface RadioProps extends RACRadioProps {
  labelPlacement?: 'start' | 'end';
  radio?: React.ReactElement | ((props: RadioRenderProps) => React.ReactNode);
  render?: never;
}

export interface CustomRenderRadioProps
  extends Omit<RACRadioProps, 'children'> {
  render:
    | string
    | React.ReactElement
    | ((props: RadioRenderProps) => React.ReactNode);
  radio?: never;
  children?: never;
}

export function Radio(props: RadioProps | CustomRenderRadioProps) {
  const descriptionContext = React.useContext(DescriptionContext);

  if (props.render !== undefined) {
    const { render, ...restProps } = props;

    return (
      <RACRadio
        {...restProps}
        aria-describedby={descriptionContext?.['aria-describedby']}
        className={composeRenderProps(
          props.className,
          (className, { isDisabled, isFocusVisible }) =>
            twMerge(
              'group text-base/6 sm:text-sm/6',
              isDisabled && 'opacity-50',
              isFocusVisible &&
                'outline-ring outline outline-2 outline-offset-2',
              className,
            ),
        )}
      >
        {render}
      </RACRadio>
    );
  }

  const { labelPlacement = 'end', radio, ...restProps } = props;

  return (
    <RACRadio
      {...restProps}
      aria-describedby={descriptionContext?.['aria-describedby']}
      data-label-placement={labelPlacement}
      className={composeRenderProps(
        props.className,
        (className, { isDisabled }) =>
          twMerge(
            'group flex items-center text-base/6 sm:text-sm/6',
            'group-aria-[orientation=horizontal]:text-nowrap',
            labelPlacement === 'start' && 'flex-row-reverse justify-between',
            isDisabled && 'opacity-50',
            className,
          ),
      )}
    >
      {(renderProps) => {
        return (
          <>
            <div
              slot="radio"
              className={twMerge(
                'grid shrink-0 place-content-center rounded-full border',
                radio ? '' : 'size-4.5 sm:size-4',
                labelPlacement === 'end' ? 'me-3' : 'ms-3',
                renderProps.isReadOnly && 'opacity-50',
                renderProps.isSelected
                  ? 'border-accent bg-accent'
                  : 'border-[oklch(from_var(--color-input)_calc(l*var(--contract,0.9))_c_h)] dark:bg-white/5 dark:[--contract:1.1]',
                renderProps.isInvalid &&
                  'border-red-600 dark:border-red-600',
                renderProps.isFocusVisible &&
                  'outline-ring outline outline-2 outline-offset-2',
              )}
            >
              {radio ? (
                typeof radio === 'function' ? (
                  radio(renderProps)
                ) : (
                  radio
                )
              ) : (
                <div
                  className={twMerge(
                    'rounded-full',
                    renderProps.isSelected &&
                      'size-2 bg-[lch(from_var(--color-accent)_calc((49.44_-_l)_*_infinity)_0_0)] sm:size-1.5',
                  )}
                ></div>
              )}
            </div>

            {typeof props.children === 'function'
              ? props.children(renderProps)
              : props.children}
          </>
        );
      }}
    </RACRadio>
  );
}
