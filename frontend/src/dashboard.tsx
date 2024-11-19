import "vite/modulepreload-polyfill";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { useQuery, QueryClient, QueryClientProvider } from "@tanstack/react-query";


// Create a client
const queryClient = new QueryClient();

// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function fetchData(url: string): Promise<any> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error("Network response was not ok");
  }
  const data = await response.json();
  return data;
}

function useData() {
  const query = useQuery({ queryKey: ["community_docs"], queryFn: () => fetchData("/api/dashboard"), staleTime: Infinity, networkMode: "online" });
  return query.data
}


export function Guidelines() {
  const data = useData();
  const text = data?.community_docs[0].text || "Loading...";
  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <h3 className="h5">Community Guidelines</h3>
      </div>
      <p className="mb-6">{text}</p>
    </>
  );
}
createRoot(document.getElementById("--react-dashboard")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <Guidelines />
    </QueryClientProvider>
  </StrictMode>
);
