import "vite/modulepreload-polyfill";
import "./style.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";

import { queryClient, useData } from "./query";

type LogEntry = {
  id: number;
  create_datetime: string;
  level: number;
  action: string;
  policy: string;
  msg: string;
};

type Logs = {
  logs: LogEntry[];
};

const LOG_LEVELS: Record<number, string> = {
  0: "NotSet",
  10: "Debug",
  20: "Info",
  30: "Warning",
  40: "Error",
  50: "Fatal",
};

const LOG_LEVEL_COLORS: Record<number, string> = {
  0: "text-grey-dark",
  10: "text-grey-dark",
  20: "text-blue-500",
  30: "text-yellow-600",
  40: "text-red-600",
  50: "text-red-800",
};

function formatDateTime(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleString();
}

export function LogsTable() {
  const data = useData<Logs>("/api/logs", "logs");

  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 h-32">
        <p className="text-grey-dark">Loading...</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="table-auto w-full">
        <thead>
          <tr className="border-b border-background-focus">
            <th className="text-left p-4">Date & Time</th>
            <th className="text-left p-4">Level</th>
            <th className="text-left p-4">Action</th>
            <th className="text-left p-4">Policy</th>
            <th className="text-left p-4">Message</th>
          </tr>
        </thead>
        <tbody>
          {data.logs.map((log) => (
            <tr key={log.id} className="border-b border-background-focus hover:bg-background-popup/20">
              <td className="p-4 text-grey-dark">
                {formatDateTime(log.create_datetime)}
              </td>
              <td className={`p-4 ${LOG_LEVEL_COLORS[log.level] || "text-grey-dark"}`}>
                {LOG_LEVELS[log.level] || log.level}
              </td>
              <td className="p-4 text-grey-dark">{log.action || "-"}</td>
              <td className="p-4 text-grey-dark">{log.policy || "-"}</td>
              <td className="p-4">{log.msg}</td>
            </tr>
          ))}
          {data.logs.length === 0 && (
            <tr>
              <td colSpan={5} className="p-4 text-center text-grey-dark">
                No logs found
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export function Logs() {
  return (
    <>
      <div className="lg:sticky lg:top-0 lg:z-30 flex gap-2 bg-white py-6 px-6 lg:py-8 lg:px-8 border-b border-background-focus justify-between">
        <h1 className="inline h3">Logs</h1>
      </div>
      <div className="lg:p-6 relative">
        <LogsTable />
      </div>
    </>
  );
}

createRoot(document.getElementById("--react-logs")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <Logs />
    </QueryClientProvider>
  </StrictMode>,
);
