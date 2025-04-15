import { twMerge } from 'tailwind-merge';
import { Icon } from '../../icon';

export function AvailableIcon({
  className,
  'aria-label': arialLabel,
  ...props
}: React.JSX.IntrinsicElements['svg']) {
  return (
    <Icon aria-label={arialLabel}>
      <svg
        className={twMerge('text-emerald-600', className)}
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 512 512"
        fill="currentColor"
        {...props}
      >
        <path d="M256 512A256 256 0 1 0 256 0a256 256 0 1 0 0 512z" />
      </svg>
    </Icon>
  );
}
