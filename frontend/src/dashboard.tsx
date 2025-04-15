import "vite/modulepreload-polyfill";

import "./style.css";
import { JSX, StrictMode, useCallback, useContext, useState } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider, useMutation } from "@tanstack/react-query";

// dont import SVG files directly because of issue with loading static assets in dev mode
// BC can't load from insecure URL, proxying dev server is annoying, and can't inline them
import CancelIcon from "./components/CancelIcon";
import PoliciesEmptyIcon from "./components/PoliciesEmptyIcon";

import { queryClient, useData } from "./query";
import {
  Dialog,
  DialogBody,
  DialogCloseButton,
  DialogFooter,
  DialogHeader,
  DialogTrigger,
} from "./react-aria-components-tailwind-starter/dialog";
import { Button } from "./react-aria-components-tailwind-starter/button";
import { Modal } from "./react-aria-components-tailwind-starter/modal";
import { Form } from "./react-aria-components-tailwind-starter/form";
import {
  FieldError,
  Input,
  Label,
  TextArea,
  TextField,
} from "./react-aria-components-tailwind-starter/field";
import { csrfHeaders } from "./csrf";
import { OverlayTriggerStateContext } from "react-aria-components";

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

export function GuidelinesModal({
  text,
  name,
}: {
  text: string;
  name: string;
}) {
  const [editedName, setEditedName] = useState<null | string>(null);
  const [editedText, setEditedText] = useState<null | string>(null);
  const dialogState = useContext(OverlayTriggerStateContext)!;

  const mutation = useMutation({
    mutationFn: (data: { text: string | null; name: string | null }) =>
      fetch("/api/community_doc", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          ...csrfHeaders(),
        },
        // credentials: "include",
        body: JSON.stringify(data),
      }).then(async (response) => {
        if (!response.ok) {
          throw new Error(await response.text());
        }
      }),
    onSuccess: () => {
      dialogState.close();
      queryClient.invalidateQueries({ queryKey: ["data"] });
    },
  });
  return (
    <>
      <DialogHeader>Community Document</DialogHeader>
      <DialogCloseButton />
      <DialogBody>
        <Form
          className="py-4"
          id="edit-profile-form"
          validationErrors={
            mutation.error ? { text: mutation.error.message } : {}
          }
        >
          <TextField isRequired
          // className="grid grid-cols-4 gap-x-4"
          >
            <Label className="ms-auto">Name</Label>
            <Input
              // className="col-span-3"
              value={editedName === null ? name : editedName}
              onChange={(e) => setEditedName(e.target.value)}
            ></Input>
          </TextField>
          <TextField
            isRequired
            // className="grid grid-cols-4 gap-x-4"
            name={"text"}
          >
            <Label className="ms-auto">Text</Label>
            <TextArea
              // className="col-span-3"
              value={editedText === null ? text : editedText}
              onChange={(e) => setEditedText(e.target.value)}
            ></TextArea>
            <FieldError className="col-span-3 col-start-2" />
          </TextField>
        </Form>
      </DialogBody>
      <DialogFooter>
        {/* No deleting for now because only one available */}
        {/* <Button className={"bg-primary-lightest text-primary-dark"}>Delete</Button> */}
        <Button
          onClick={(e) => {
            e.preventDefault();
            mutation.mutate({ text: editedText, name: editedName });
          }}
          isDisabled={(editedText === null && editedName === null) || mutation.isPending}
          form="edit-profile-form"
          type="submit"
          className={"bg-primary-dark"}
        >
          {mutation.isPending ? "Saving..." : "Save"}
        </Button>
      </DialogFooter>
    </>
  );
}

export function Guidelines() {
  const data = useDashboardData();
  const doc = data?.community_docs[0];

  return (
    <section className="px-8 py-7 mt-4 border border-background-focus rounded-lg bg-background-light">
      <div className="flex items-center justify-between mb-4">
        <h3 className="h5">{doc?.name || "Loading..."}</h3>
        <DialogTrigger>
          <Button isDisabled={data === undefined} className={"bg-primary-dark"}>
            Details
          </Button>
          <Modal size="md" classNames={{ modalOverlay: "z-100" }}>
            <Dialog>
              <GuidelinesModal
                text={doc?.text || "Loading..."}
                name={doc?.name || "Loading..."}
              />
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
        <a href={addURL || undefined} className="button primary medium">
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

export function ProposalsList({
  proposals,
}: {
  proposals: ProposalSummary[] | undefined;
}) {
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
            <span className="text-grey-dark">
              {proposal.action.description}
            </span>{" "}
            action {proposal.status} from{" "}
            <span className="text-grey-dark">{proposal.policy.name}</span>{" "}
            policy
            {proposal.initiator.readable_name ? (
              <>
                {" "}
                by{" "}
                <span className="text-grey-dark">
                  {proposal.initiator.readable_name}
                </span>
              </>
            ) : null}
          </p>
          <p className="text-grey-light">
            {new Date(proposal.proposal_time).toLocaleString()}
          </p>
        </li>
      ))}
    </ol>
  );
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
