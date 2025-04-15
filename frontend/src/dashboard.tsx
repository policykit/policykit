import "vite/modulepreload-polyfill";

import "./style.css";
import { JSX, StrictMode, useCallback, useState } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";

// dont import SVG files directly because of issue with loading static assets in dev mode
// BC can't load from insecure URL, proxying dev server is annoying, and can't inline them
import CancelIcon from "./components/CancelIcon";
import PoliciesEmptyIcon from "./components/PoliciesEmptyIcon";

import { queryClient, useData } from "./query";
import { Dialog, DialogBody, DialogCloseButton, DialogFooter, DialogHeader, DialogTrigger } from "./react-aria-components-tailwind-starter/dialog";
import { Button } from "./react-aria-components-tailwind-starter/button";
import { Modal } from "./react-aria-components-tailwind-starter/modal";
import { Form } from "./react-aria-components-tailwind-starter/form";
import { FieldError, Input, Label, TextField } from "./react-aria-components-tailwind-starter/field";

type PolicySummary = {
  id: number;
  name: string;
  description: string;
};

type ActionSummary = {
  id: number;
  action_type: string;
  description: string;
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
  pending_proposals: ProposalSummary[];
  completed_proposals: ProposalSummary[];
  name: string;
};

function useDashboardData(): CommunityDashboard | undefined {
  return useData<CommunityDashboard>("/api/dashboard", "data");
}

export function Welcome() {
  const name = useDashboardData()?.name || "...";
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
  const data = useDashboardData();
  const doc = data?.community_docs[0];
  return (
    <section className="px-8 py-7 mt-4 border border-background-focus rounded-lg bg-background-light">
      <div className="flex items-center justify-between mb-4">
        <h3 className="h5 bg-zinc-950/25">{doc?.name || "Loading..."}</h3>
        <DialogTrigger>
          <Button>Details</Button>
          <Modal size="md">
            <Dialog>
              <DialogHeader>{doc?.name || "Loading..."}</DialogHeader>
              <DialogCloseButton />
              <DialogBody>
                <p>{doc?.text || "Loading..."}</p>
                <Form className="py-4" id="edit-profile-form">
                  <TextField isRequired className="grid grid-cols-4 gap-x-4">
                    <Label className="ms-auto">Name</Label>
                    <Input className="col-span-3"></Input>
                    <FieldError className="col-span-3 col-start-2" />
                  </TextField>
                  <TextField isRequired className="grid grid-cols-4 gap-x-4">
                    <Label className="ms-auto">Username</Label>
                    <Input className="col-span-3"></Input>
                    <FieldError className="col-span-3 col-start-2" />
                  </TextField>
                </Form>
              </DialogBody>
              <DialogFooter>
                <DialogCloseButton>Cancel</DialogCloseButton>
                <Button form="edit-profile-form" type="submit">
                  Save changes
                </Button>
              </DialogFooter>
            </Dialog>
          </Modal>
        </DialogTrigger>
      </div>
      <p className="mb-6">{doc?.text || "Loading..."}</p>
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
  const data = useDashboardData();
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

export function ProposalsList({proposals}: {proposals: ProposalSummary[] | undefined}) {
  if (!proposals) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 h-32">
        <p className="text-grey-dark">Loading...</p>
      </div>
    );
  }
  if (proposals.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 h-32">
        <p className="text-grey-dark">No Proposals</p>
      </div>
    );
  }
  return (
    <ol>
      {proposals.map((proposal) => (
        <li key={proposal.id} className="py-2">
          <p className="text-grey-darkest">
          <span className="text-grey-dark">{proposal.action.description}</span> action {" "}
          {proposal.status} from <span className="text-grey-dark">{proposal.policy.name}</span> policy
          {proposal.initiator.readable_name ? (<> by <span className="text-grey-dark">{proposal.initiator.readable_name}</span></>) : null}
          </p>
          <p className="text-grey-light">{new Date(proposal.proposal_time).toLocaleString()}</p>
        </li>
      ))}
    </ol>
  )
  
}

export function Proposals() {
  const data = useDashboardData();
  return (
    <div>
      <h3 className="h5">Pending Proposals</h3>
      <ProposalsList proposals={data?.pending_proposals} />
      <h3 className="h5">Completed Proposals</h3>
      <ProposalsList proposals={data?.completed_proposals} />
    </div>
  );
}

export function Dashboard() {
  const data = useDashboardData();
  return (
    <>
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
    <div className="lg:p-6 lg:col-span-3 border-l border-background-focus">
      <Proposals />
    </div>
    </>
  );
}

createRoot(document.getElementById("--react-dashboard")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <Dashboard />
    </QueryClientProvider>
  </StrictMode>,
);
