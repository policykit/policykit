import { Icon } from '../../icon';

export function MinusIcon({
    'aria-label': arialLabel,
    ...props
  }: React.JSX.IntrinsicElements['svg']) {
    return (
      <Icon aria-label={arialLabel}>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          {...props}
        >
          <path d="M5 12h14" />
        </svg>
      </Icon>
    );
  }