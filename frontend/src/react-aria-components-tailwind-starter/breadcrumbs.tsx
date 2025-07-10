import {
  Breadcrumb as RACBreadcrumb,
  Breadcrumbs as RACBreadcrumbs,
  BreadcrumbProps as RACBreadcrumbProps,
  BreadcrumbsProps as RACBreadcrumbsProps,
  LinkProps,
  composeRenderProps,
} from 'react-aria-components';
import { twMerge } from 'tailwind-merge';
import { Link } from './link';
import { ChevronRightIcon } from './icons/outline/chevron-right';

export function Breadcrumbs<T extends object>({
  className,
  ...props
}: RACBreadcrumbsProps<T>) {
  return (
    <RACBreadcrumbs {...props} className={twMerge('flex gap-1', className)} />
  );
}

type BreadcrumbProps = RACBreadcrumbProps & LinkProps;

export function Breadcrumb(props: BreadcrumbProps) {
  return (
    <RACBreadcrumb
      {...props}
      className={composeRenderProps(
        props.className as RACBreadcrumbProps['className'],
        (className) => {
          return twMerge('flex items-center gap-1', className);
        },
      )}
    >
      <Link
        {...props}
        className={({ isDisabled, isHovered }) => {
          return twMerge(
            'underline underline-offset-2',
            isDisabled && 'opacity-100',
            !isHovered && 'decoration-muted',
          );
        }}
      />
      {props.href && <ChevronRightIcon className="text-muted size-4" />}
    </RACBreadcrumb>
  );
}
