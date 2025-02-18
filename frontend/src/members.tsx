import "vite/modulepreload-polyfill";
import { StrictMode, useMemo } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";

// dont import SVG files directly because of issue with loading static assets in dev mode
// BC can't load from insecure URL, proxying dev server is annoying, and can't inline them
import { queryClient, useData } from "./query";

type MembersRoleSummary = {
  id: number;
  name: string;
  user_ids: number[];
};

type MemberSummary = {
  id: number;
  name: string;
  avatar: string;
};

type Members = {
  members: MemberSummary[];
  roles: MembersRoleSummary[];
};

export function MembersTable() {
  const data = useData<Members>("/api/members", "members");

  const userToRoles: Map<number, string[]> = useMemo(() => {
    if (!data) {
      return new Map();
    }
    const userToRoles = new Map();
    for (const role of data.roles) {
      for (const user_id of role.user_ids) {
        if (!userToRoles.has(user_id)) {
          userToRoles.set(user_id, []);
        }
        userToRoles.get(user_id)!.push(role.name);
      }
    }
    return userToRoles;
  }, [data]);

  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 h-32">
        <p className="text-grey-dark">Loading...</p>
      </div>
    );
  }
  return (
    <table className="table-auto">
      <tbody>
        <tr>
          <th className="text-left">Name</th>
          <th className="text-left">Roles</th>
        </tr>
        {data.members.map((member) => (
          <tr key={member.id}>
            <td>
              <span className="text-grey-dark">{member.name}</span>
            </td>
            <td>{(userToRoles.get(member.id) || []).join(", ")}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function Members() {
  return (
    <>
      <div className="lg:sticky lg:top-0 lg:z-30 flex gap-2 bg-white py-6 px-6 lg:py-8 lg:px-8 border-b border-background-focus justify-between">
        <h1 className="inline h3">Members</h1>
      </div>
      <div className="lg:p-6 relative">
        <MembersTable />
      </div>
    </>
  );
}

createRoot(document.getElementById("--react-members")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <Members />
    </QueryClientProvider>
  </StrictMode>,
);
