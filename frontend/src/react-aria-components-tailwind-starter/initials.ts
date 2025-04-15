const GRADIENTS: Array<[string, string]> = [
  ['oklch(0.55 0.016 285.938)', 'oklch(0.705 0.015 286.067)'],
  ['oklch(0.4885 0.1834 3.96)', 'oklch(0.7134 0.1638 2.77)'],
  ['oklch(0.5348 0.2679 282.44)', 'oklch(0.677 0.1533 284.96)'],
  ['oklch(0.4309 0.1865 281.4)', 'oklch(0.677 0.1533 284.96)'],
  ['oklch(0.3034 0.0964 306.25)', 'oklch(0.644 0.0971 304.93)'],
  ['oklch(0.7376 0.081 170.77)', 'oklch(0.8015 0.1603 138.01)'],
  ['oklch(0.6273 0.0715 205.19)', 'oklch(0.8188 0.0649 173.43)'],
  ['oklch(0.52 0.0614 123.17)', 'oklch(0.7395 0.1053 118.44)'],
  ['oklch(0.3496 0.0988 145.03)', 'oklch(0.6515 0.0609 168.71)'],
  ['oklch(0.6475 0.1768 249.33)', 'oklch(0.813 0.1094 235.78)'],
  ['oklch(0.5495 0.1202 251.83)', 'oklch(0.7475 0.0724 250.72)'],
  ['oklch(0.5126 0.0738 237.27)', 'oklch(0.7352 0.0479 227.03)'],
  ['oklch(0.6368 0.1388 28.08)', 'oklch(0.8143 0.0907 51.75)'],
  ['oklch(0.7593 0.164 64.36)', 'oklch(0.8769 0.179577 93.1299)'],
  ['oklch(0.4815 0.0401 14.22)', 'oklch(0.7406 0.0305 77.47)'],
];

export type FallbackAvatarProps = { fallback?: 'initials' | 'icon' } & (
  | {
      colorful?: boolean;
      background?: never;
    }
  | {
      colorful?: never;
      background?: string;
    }
);

export function getInitials(name: string) {
  return name
    .split(/\s/)
    .map((part) => part.substring(0, 1))
    .filter((v) => !!v)
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

function sumChars(str: string) {
  let sum = 0;
  for (let i = 0; i < str.length; i++) {
    sum += str.charCodeAt(i);
  }

  return sum;
}

function getInitialsGradient(
  name: string,
  colorful?: boolean,
): [string, string] {
  if (colorful) {
    const i = sumChars(name) % GRADIENTS.length;
    return GRADIENTS[i];
  }

  return GRADIENTS[0];
}

export function getFallbackAvatarDataUrl({
  alt,
  fallback,
  colorful,
  background,
}: {
  alt: string;
} & FallbackAvatarProps) {
  const initials = getInitials(alt);

  background =
    background ??
    `linear-gradient(135deg, ${getInitialsGradient(alt, colorful).join(', ')})`;

  return fallback === 'icon'
    ? getFallbackIconDateUrl(background)
    : getFallbackInitialsDataUrl(background, initials);
}

function getFallbackIconDateUrl(bg: string) {
  return (
    'data:image/svg+xml;base64,' +
    btoa(
      `<svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 80 80" style="background:${bg};color:oklch(0.985 0 0);"><g><path d="M 8 80 a 28 24 0 0 1 64 0"/><circle cx="40" cy="32" r="16"/></g></svg>`,
    )
  );
}

function getFallbackInitialsDataUrl(bg: string, initials: string) {
  return (
    'data:image/svg+xml;base64,' +
    btoa(
      `<svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 24 24" style="background:${bg};color:oklch(0.985 0 0);font-family:system-ui;"><text x="50%" y="50%" alignment-baseline="middle" dominant-baseline="middle" text-anchor="middle" dy=".125em" font-size="65%">${initials}</text></svg>`,
    )
  );
}
