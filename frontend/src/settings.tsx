import "vite/modulepreload-polyfill";
import "./style.css";
import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient, useData } from "./query";

type Integration = {
  name: string;
  config: [string, string][];
  webhook_url?: string;
  description?: string;
  image_url?: string;
  id?: string;
};

type SettingsData = {
  enabled_integrations: [string, Integration][];
  disabled_integrations: [string, Integration][];
};

function useSettingsData(): SettingsData | undefined {
  return useData<SettingsData>("/api/settings", "settings");
}

type TabKey = "About" | "Integrations";

function TabButton({ children, isActive, onClick }: { children: React.ReactNode; isActive: boolean; onClick: () => void }) {
  return (
    <button
      className={`px-6 py-2 border-b-2 mb-[-2px] ${isActive ? 'text-primary border-primary-dark' : 'border-transparent text-grey-dark hover:text-grey-darkest'}`}
      onClick={onClick}
      type="button"
      role="tab"
      aria-selected={isActive}
    >
      {children}
    </button>
  );
}

function AboutTab() {
  return (
    <section className="mt-8">
      <h2 className="h3 mb-8">About</h2>
      <div className="lg:grid lg:grid-cols-10 gap-8">
        <div className="lg:col-span-6">
          <p className="large mb-6">
            PolicyKit empowers online community members to concisely author a wide range of governance procedures and automatically carry out those procedures on their home platforms.
          </p>
          <p>
            Inspired by Nobel economist Elinor Ostrom, we've developed a framework that describes governance as a series of actions and policies, written in short programming scripts. We're now building out an editor, software libraries, and connectors to platforms like Slack, Reddit, and Discord for communities to author actions and policies.
          </p>
        </div>
        <div className="lg:col-span-3 lg:col-start-8 space-y-8 mt-8 lg:mt-0">
          <div>
            <h3 className="p font-medium mb-2">Join our community</h3>
            <div className="flex flex-col gap-1">
              <a href="https://discord.gg/p9PzjM4vcv" target="_blank" rel="noopener noreferrer" className="p small text-primary-dark hover:text-primary">
                Discord
              </a>
              <a href="https://policykit.us17.list-manage.com/subscribe/post?u=4a1d75598cb903abe5974f90d&id=07499cff74" target="_blank" rel="noopener noreferrer" className="p small text-primary-dark hover:text-primary">
                Mailing List
              </a>
            </div>
          </div>
          <div>
            <h3 className="p font-medium mb-2">Contribute</h3>
            <div className="flex flex-col gap-1">
              <a href="https://docs.google.com/forms/d/e/1FAIpQLSdB_BE_iKX8TaPXHkBK_t0I8lSnux_IEtV0w4Fy7zqDqFyVtQ/viewform?usp=sf_link" target="_blank" rel="noopener noreferrer" className="p small text-primary-dark hover:text-primary">
                Feedback Form
              </a>
              <a href="https://github.com/amyxzhang/policykit" target="_blank" rel="noopener noreferrer" className="p small text-primary-dark hover:text-primary">
                GitHub
              </a>
              <a href="https://policykit.readthedocs.io/en/latest/index.html" target="_blank" rel="noopener noreferrer" className="p small text-primary-dark hover:text-primary">
                Documentation
              </a>
            </div>
          </div>
          <div>
            <h3 className="p font-medium mb-2">Our research</h3>
            <div className="flex flex-col gap-1">
              <a href="https://social.cs.washington.edu/index.html" target="_blank" rel="noopener noreferrer" className="p small text-primary-dark hover:text-primary">
                Social Futures Lab
              </a>
              <a href="https://arxiv.org/abs/2008.04236" target="_blank" rel="noopener noreferrer" className="p small text-primary-dark hover:text-primary">
                Our ACM UIST 2020 Paper
              </a>
              <a href="https://vimeo.com/446531759" target="_blank" rel="noopener noreferrer" className="p small text-primary-dark hover:text-primary">
                Our ACM UIST 2020 Video
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function IntegrationsTab() {
  const data = useSettingsData();

  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 h-32 mt-8">
        <p className="text-grey-dark">Loading...</p>
      </div>
    );
  }

  return (
    <section className="mt-8">
      <div className="flex justify-between items-center mb-8">
        <h2 className="h3">Integrations</h2>
        <a href="/main/settings/addintegration" className="button primary medium">
          Add Integration
        </a>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {data.enabled_integrations.length === 0 ? (
          <p className="text-grey-dark col-span-full">No integrations enabled.</p>
        ) : (
          data.enabled_integrations.map(([name, integration]) => (
            <div key={name} className="px-6 py-4 border-2 border-gray-200 rounded-lg bg-white">
              <h3 className="h5 font-medium mb-2">{name}</h3>
              {integration.description && (
                <p className="text-grey-dark text-sm mb-4">{integration.description}</p>
              )}
              {integration.config && integration.config.length > 0 && (
                <div className="space-y-2">
                  {integration.config.map(([key, value]) => (
                    <div key={key} className="text-sm">
                      <span className="font-medium text-grey-darkest">{key}: </span>
                      <span className="text-grey-dark">{value}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </section>
  );
}

export function Settings() {
  const [currentTab, setCurrentTab] = useState<TabKey>(() => {
    const params = new URLSearchParams(window.location.search);
    const tab = params.get('tab');
    return (tab === 'Integrations' ? 'Integrations' : 'About') as TabKey;
  });

  const handleTabChange = (tab: TabKey) => {
    setCurrentTab(tab);
    const url = new URL(window.location.href);
    url.searchParams.set('tab', tab);
    window.history.pushState(null, '', url.toString());
  };

  return (
    <>
      <div className="lg:sticky lg:top-0 lg:z-30 bg-white border-b border-background-focus">
        <div className="px-6 lg:px-8 py-6 lg:py-8">
          <h1 className="h3">Settings</h1>
        </div>
        <div className="px-6 lg:px-8">
          <ul role="tablist" className="flex items-stretch border-b-2 border-gray-200">
            <li>
              <TabButton isActive={currentTab === 'About'} onClick={() => handleTabChange('About')}>
                About
              </TabButton>
            </li>
            <li>
              <TabButton isActive={currentTab === 'Integrations'} onClick={() => handleTabChange('Integrations')}>
                Integrations
              </TabButton>
            </li>
          </ul>
        </div>
      </div>
      <div className="px-6 lg:px-8 pb-16">
        {currentTab === 'About' && <AboutTab />}
        {currentTab === 'Integrations' && <IntegrationsTab />}
      </div>
    </>
  );
}

createRoot(document.getElementById("--react-settings")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <Settings />
    </QueryClientProvider>
  </StrictMode>,
);
