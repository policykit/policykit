import "vite/modulepreload-polyfill";
import { StrictMode, useCallback, useState } from "react";
import { createRoot } from "react-dom/client";

// dont import SVG files directly because of issue with loading static assets in dev mode
// BC can't load from insecure URL, proxying dev server is annoying, and can't inline them
import CancelIcon from "./components/CancelIcon";
import PoliciesEmptyIcon from "./components/PoliciesEmptyIcon";

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

type PolicySummary = {
  id: number;
  name: string;
  description: string;
};

type ActionSummary = {
  id: number;
  action_type: string;
};

type InitiatorSummary = {
  id: number;
  readable_name: string;
};

type ProposalSummary = {
  id: number;
  status: string;
  proposal_time: string;
  is_vote_closed: boolean;
  action: ActionSummary;
  initiator: InitiatorSummary;
  policy: PolicySummary;
};

type CommunityDoc = {
  id: number;
  name: string;
  text: string;
};

type DashboardRoleSummary = {
  id: number;
  name: string;
  description: string;
  number_of_members: number;
};

type CommunityDashboard = {
  roles: DashboardRoleSummary[];
  community_docs: CommunityDoc[];
  trigger_policies: PolicySummary[];
  platform_policies: PolicySummary[];
  constitution_policies: PolicySummary[];
  proposals: ProposalSummary[];
  name: string;
};

function useData(): CommunityDashboard | undefined {
  const query = useQuery<CommunityDashboard>({
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
          <CancelIcon className="stroke-primary-dark" />
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

export function Policies({
  policies,
  type,
  addURL,
}: {
  policies: undefined | PolicySummary[];
  type: string | null;
  addURL: string | null;
}) {
  let policiesElement;
  if (!policies) {
    policiesElement = (
      <div className="flex flex-col items-center justify-center gap-4 h-32">
        <p className="text-grey-dark">Loading...</p>
      </div>
    );
  } else {
    if (policies.length == 0) {
      policiesElement = (
        <div className="flex flex-col items-center justify-center gap-4 h-32">
          <PoliciesEmptyIcon />
          <p className="text-grey-dark">No Policies yet</p>
        </div>
      );
    } else {
      policiesElement = (
        <DashboardTable
          rows={policies.map((policy) => ({
            title: policy.name,
            description: policy.description,
            details: <></>,
          }))}
        />
      );
    }
  }
  const header = type ? `${type} Policies` : "Policies";
  return (
    <section className="px-8 py-7 mt-4 border border-background-focus rounded-lg bg-white">
      <div className="flex items-center justify-between mb-4">
        <h3 className="h5">{header}</h3>
        <a
          href={addURL || undefined}
          className="button primary medium"
          // x-data
          // @click="$dispatch('toggle_modal')"
          // hx-get="/main/policynew"
          // hx-push-url="true"
          // hx-target="#modal-content"
          // hx-swap="innerHTML transition:true"
        >
          Add
        </a>
      </div>

      {policiesElement}
    </section>
  );
}

type DashboardTableRow = {
  title: string;
  description: string;
  details: JSX.Element;
};

export function DashboardTable({ rows }: { rows: DashboardTableRow[] }) {
  return (
    <table className="table-auto">
      <tbody>
        {rows.map((row, i) => (
          <tr key={i}>
            <td>
              <h4 className="h5">{row.title}</h4>
            </td>
            <td>
              <span className="text-grey-dark">{row.description}</span>
            </td>
            <td>{row.details}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function Roles({
  roles,
}: {
  roles: DashboardRoleSummary[] | undefined;
}) {
  let rolesList;
  if (!roles) {
    rolesList = <p className="text-grey-dark">Loading...</p>;
  } else {
    rolesList = (
      <DashboardTable
        rows={roles.map((role) => ({
          title: role.name,
          description: role.description,
          details: (
            <span className="text-grey-dark">
              {role.number_of_members === 1
                ? "1 member"
                : `${role.number_of_members} members`}
            </span>
          ),
        }))}
      />
    );
  }
  return (
    <section className="px-8 py-7 mt-4 border border-background-focus rounded-lg bg-white">
      <div className="flex items-center justify-between mb-4">
        <h3 className="h5">Roles</h3>
      </div>
      {rolesList}
    </section>
  );
}

export function MetaGovernance() {
  const data = useData();
  return (
    <section className="px-8 py-7 mt-4 border border-background-focus rounded-lg bg-background-light">
      <p className="text-grey-dark">Meta-Governance</p>
      <Policies
        type="Constitutional"
        policies={data?.constitution_policies}
        addURL={null}
      />
      <Roles roles={data?.roles} />
    </section>
  );
}

export function Dashboard() {
  const data = useData();
  return (
    <div className="lg:p-6 lg:col-span-7">
      <Welcome />
      <Guidelines />
      <Policies
        type={null}
        policies={
          data
            ? [...data.trigger_policies, ...data.platform_policies]
            : undefined
        }
        addURL={"/no-code/main"}
      />
      <MetaGovernance />
    </div>
  );
}

createRoot(document.getElementById("--react-dashboard")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <Dashboard />
    </QueryClientProvider>
  </StrictMode>,
);
