import React from 'react';

export type TimeOption = {
  hour: number;
  minute: number;
  value: string;
  id: string;
};

export function useTimePicker({
  intervalInMinute,
}: {
  intervalInMinute: 15 | 30;
}): Array<TimeOption> {
  return React.useMemo(() => {
    const options = [];

    for (let hour = 0; hour < 24; hour++) {
      const period = hour >= 12 ? 'PM' : 'AM';
      let hourIn12Format = hour % 12;

      if (hourIn12Format === 0) {
        hourIn12Format = 12;
      }

      for (
        let interval = 0;
        interval < Math.floor(60 / intervalInMinute);
        interval++
      ) {
        const minutes = interval * intervalInMinute;
        options.push({
          hour,
          minute: minutes,
          value: `${hourIn12Format}:${minutes === 0 ? '00' : minutes} ${period}`,
          id: `${hourIn12Format}:${minutes === 0 ? '00' : minutes} ${period}`,
        });
      }
    }

    return options;
  }, [intervalInMinute]);
}

export function getRoundMinute({
  intervalInMinute,
  minute,
}: {
  intervalInMinute: number;
  minute: number;
}) {
  const closeMinute = Array(60 / intervalInMinute + 1)
    .fill(0)
    .map((_, i) => {
      return intervalInMinute * i;
    })
    .find((i) => {
      return i > minute;
    });

  if (closeMinute) {
    return closeMinute - minute;
  }

  return 0;
}
