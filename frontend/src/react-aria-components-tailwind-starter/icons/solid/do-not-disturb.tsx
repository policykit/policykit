import { twMerge } from 'tailwind-merge';
import { Icon } from '../../icon';

export function DoNotDisturbIcon({
  className,
  'aria-label': arialLabel,
  ...props
}: React.JSX.IntrinsicElements['svg']) {
  return (
    <Icon aria-label={arialLabel}>
      <svg
        fill="currentColor"
        className={twMerge('text-red-600', className)}
        aria-hidden="true"
        viewBox="0 0 10 10"
        xmlns="http://www.w3.org/2000/svg"
        {...props}
      >
        <path
          d="M5 10A5 5 0 1 0 5 0a5 5 0 0 0 0 10ZM3.5 4.5h3a.5.5 0 0 1 0 1h-3a.5.5 0 0 1 0-1Z"
          fill="currentColor"
        ></path>
      </svg>
    </Icon>
  );
}
