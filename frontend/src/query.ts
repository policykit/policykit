import { QueryClient, useQuery } from "@tanstack/react-query";

// Create a client
export const queryClient = new QueryClient();

// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function fetchData(url: string): Promise<any> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error("Network response was not ok");
  }
  const data = await response.json();
  return data;
}




export function useData<T>(url: string, key: string): T | undefined {
  const query = useQuery<T>({
    queryKey: [key],
    queryFn: () => fetchData(url),
    staleTime: Infinity,
    networkMode: "online",
  });
  return query.data;
}
