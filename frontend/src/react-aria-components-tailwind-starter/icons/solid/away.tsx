import { twMerge } from 'tailwind-merge';
import { Icon } from '../../icon';

export function AwayIcon({
  className,
  'aria-label': arialLabel,
  ...props
}: React.JSX.IntrinsicElements['svg']) {
  return (
    <Icon aria-label={arialLabel}>
      <svg
        className={twMerge('text-slate-400', className)}
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 512 512"
        fill="none"
        stroke="currentColor"
        strokeWidth="90"
        strokeLinecap="round"
        strokeLinejoin="round"
        {...props}
      >
        <circle cx="256" cy="256" r="213" />
      </svg>
    </Icon>
  );
}
