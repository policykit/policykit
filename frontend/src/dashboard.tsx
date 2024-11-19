import "vite/modulepreload-polyfill";
import { StrictMode, useCallback, useState } from "react";
import { createRoot } from "react-dom/client";

import cancelIcon from "./icons/cancel.svg";
import policiesEmptyIcon from "./icons/cancel.svg";

import {
  useQuery,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";

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
  const query = useQuery({
    queryKey: ["community_docs"],
    queryFn: () => fetchData("/api/dashboard"),
    staleTime: Infinity,
    networkMode: "online",
  });
  return query.data;
}

export function Welcome() {
  const name = useData()?.name || "...";
  const [show, setShow] = useState(true);
  const hide = useCallback(() => setShow(false), [setShow]);
  if (!show) {
    return <></>;
  }

  return (
    <section className="px-8 py-7 bg-primary-lightest rounded-lg">
      <div className="flex items-center justify-between mb-8">
        <h2 className="h4 ">Welcome to {name}'s governance dashboard</h2>
        <button onClick={hide}>
          <img
            className="stroke-primary-dark"
            alt="cancel icon"
            src={cancelIcon}
          />
        </button>
      </div>
      <p className="mb-6">
        If you have any questions or need help getting started, don't hesitate
        to reach out. We're here to help you build and evolve a thriving online
        community.
      </p>
      <div className="flex justify-end ">
        <a href="#" className="button primary medium">
          Share your feedback
        </a>
      </div>
    </section>
  );
}
export function Guidelines() {
  const data = useData();
  const text = data?.community_docs[0].text || "Loading...";
  return (
    <section className="px-8 py-7 mt-4 border border-background-focus rounded-lg bg-background-light">
      <div className="flex items-center justify-between mb-4">
        <h3 className="h5">Community Guidelines</h3>
      </div>
      <p className="mb-6">{text}</p>
    </section>
  );
}

export function Policies() {
  return (
    <section className="px-8 py-7 mt-4 border border-background-focus rounded-lg">
      <div className="flex items-center justify-between mb-4">
        <h3 className="h5">Policies</h3>
        <button
          // href="#"
          className="button primary medium"
          // x-data
          // @click="$dispatch('toggle_modal')"
          // hx-get="/main/policynew"
          // hx-push-url="true"
          // hx-target="#modal-content"
          // hx-swap="innerHTML transition:true"
        >
          Add
        </button>
      </div>
      <div className="flex flex-col items-center justify-center gap-4 h-32">
        <img alt="empty policies icon" src={policiesEmptyIcon} />
        <p className="text-grey-dark">No Policies yet</p>
      </div>
    </section>
  );
}

export function Dashboard() {
  return (<>
    <Welcome />
    <Guidelines />
    <Policies />
    <div className="h-80" />
  </>);
}

createRoot(document.getElementById("--react-dashboard")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <Dashboard />
    </QueryClientProvider>
  </StrictMode>,
);
