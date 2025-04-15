import { Icon } from '../../icon';

export function ImageIcon({
  'aria-label': arialLabel,
  ...props
}: React.JSX.IntrinsicElements['svg']) {
  return (
    <Icon aria-label={arialLabel}>
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="24"
        height="24"
        viewBox="0 0 20 20"
        fill="currentColor"
        {...props}
      >
        <path
          fill="currentColor"
          d="M18 3H2a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1V4a1 1 0 0 0-1-1m-4.75 3.5a1.25 1.25 0 1 1 0 2.5a1.25 1.25 0 0 1 0-2.5M4 14l3.314-7.619l3.769 6.102l3.231-1.605L16 14z"
        ></path>
      </svg>
    </Icon>
  );
}
