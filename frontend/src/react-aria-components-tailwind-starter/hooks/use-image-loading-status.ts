import React from 'react';

type ImageLoadingStatus = 'idle' | 'loading' | 'loaded' | 'error';

export function useImageLoadingStatus(src?: string) {
  const [loadingStatus, setLoadingStatus] =
    React.useState<ImageLoadingStatus>('idle');

  React.useLayoutEffect(() => {
    if (!src) {
      setLoadingStatus('error');
      return;
    }

    let isMounted = true;
    const image = new window.Image();

    const updateStatus = (status: ImageLoadingStatus) => () => {
      if (!isMounted) return;
      setLoadingStatus(status);
    };

    setLoadingStatus('loading');
    image.onload = updateStatus('loaded');
    image.onerror = updateStatus('error');
    image.src = src;

    return () => {
      isMounted = false;
    };
  }, [src]);

  return loadingStatus;
}
