import DashboardFilesPanel from "../components/DashboardFilesPanel";
import { Tabs, TabList, Tab, TabPanels, TabPanel } from "../components/Tabs";
import { useRedactedFiles } from "../hooks/useRedacted_files";
import { useCurrentUser } from "../hooks/useLoadUser";
import AnimatedLandingHeader from "../components/AnimatedLandingHeader";
import Upload from "./Upload";
import { Button } from "../components/button";

function StatCard({ label, value, tone = "default" }) {
  const toneClass =
    tone === "accent"
      ? "border-cyan-300/30 bg-cyan-300/10 text-cyan-100"
      : "border-white/10 bg-white/5 text-white";

  return (
    <div className={`rounded-3xl border p-5 ${toneClass}`}>
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-300">
        {label}
      </p>
      <p className="mt-3 text-3xl font-semibold">{value}</p>
    </div>
  );
}

function Dashboard() {
  const {
    user,
    loading: userLoading,
    error: userError,
    reload: reloadUser,
  } = useCurrentUser();
  const {
    files,
    loading: filesLoading,
    error: filesError,
    reload: reloadFiles,
  } = useRedactedFiles();

  const displayName = user?.first_name || "there";
  const latestFile = files[0]?.filename || "No scans yet";
  const handleRetryAll = () => {
    reloadUser();
    reloadFiles();
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.18),_transparent_32%),linear-gradient(180deg,_#020617_0%,_#0f172a_52%,_#111827_100%)] px-4 py-8 text-white sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-8">
        <section className="overflow-hidden rounded-[2rem] border border-white/10 bg-slate-950/70 p-8 shadow-2xl backdrop-blur">
          <div className="grid gap-8 lg:grid-cols-[minmax(0,1.3fr)_minmax(280px,0.7fr)]">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-cyan-200">
                Operations Dashboard
              </p>
              <h1 className="mt-4 text-4xl font-semibold tracking-tight text-white sm:text-5xl">
                Welcome back, {displayName}
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
                Track redacted outputs, manage uploads, and keep an eye on your
                current account state without losing access to key actions when
                one data source is empty.
              </p>
            </div>

            <div className="rounded-[1.75rem] border border-cyan-300/20 bg-cyan-300/10 p-6">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-100">
                Recent Activity
              </p>
              <p className="mt-4 text-xl font-semibold text-white">
                {filesLoading ? "Loading latest output..." : latestFile}
              </p>
              <p className="mt-2 text-sm text-cyan-50/80">
                Latest generated asset available for download and reporting.
              </p>
              {(userError || filesError) && (
                <div className="mt-5 rounded-2xl border border-amber-300/30 bg-amber-300/10 p-4 text-sm text-amber-100">
                  One or more dashboard requests failed.
                  <div className="mt-3">
                    <Button onClick={handleRetryAll}>
                      Retry dashboard data
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Redacted Files"
            value={filesLoading ? "..." : files.length}
            tone="accent"
          />
          <StatCard
            label="Account Tier"
            value={userLoading ? "..." : user?.tier || "Unknown"}
          />
          <StatCard
            label="Profile Email"
            value={userLoading ? "..." : user?.email || "Unavailable"}
          />
          <StatCard
            label="Status"
            value={
              userError || filesError
                ? "Attention"
                : userLoading || filesLoading
                  ? "Syncing"
                  : "Ready"
            }
          />
        </section>

        <Tabs defaultvalue="files">
          <TabList>
            <Tab value="files">Redacted Files</Tab>
            <Tab value="info">Your Info</Tab>
            <Tab value="upload">Upload</Tab>
          </TabList>

          <TabPanels>
            <TabPanel value="files">
              <DashboardFilesPanel
                files={files}
                loading={filesLoading}
                error={filesError}
                onRetry={reloadFiles}
              />
            </TabPanel>

            <TabPanel value="info">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-300">
                    Account Snapshot
                  </p>
                  {userLoading ? (
                    <p className="mt-4 text-sm text-slate-300">
                      Loading account details...
                    </p>
                  ) : userError ? (
                    <>
                      <p className="mt-4 text-sm text-rose-200">
                        {userError.message}
                      </p>
                      <div className="mt-4">
                        <Button onClick={reloadUser}>Retry user load</Button>
                      </div>
                    </>
                  ) : (
                    <dl className="mt-4 space-y-4 text-sm">
                      <div>
                        <dt className="text-slate-400">User ID</dt>
                        <dd className="mt-1 font-medium text-white">
                          {user?.user_id || "Unavailable"}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-slate-400">Email</dt>
                        <dd className="mt-1 font-medium text-white">
                          {user?.email || "Unavailable"}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-slate-400">Role</dt>
                        <dd className="mt-1 font-medium capitalize text-white">
                          {user?.role || "Unavailable"}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-slate-400">Company</dt>
                        <dd className="mt-1 font-medium text-white">
                          {user?.company_name || "Unavailable"}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-slate-400">Tier</dt>
                        <dd className="mt-1 font-medium capitalize text-white">
                          {user?.tier || "Unavailable"}
                        </dd>
                      </div>
                    </dl>
                  )}
                </div>

                <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-300">
                    Next Action
                  </p>
                  <p className="mt-4 text-lg font-semibold text-white">
                    {files.length
                      ? "Review your latest outputs"
                      : "Run your first scan"}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-slate-300">
                    Use the Upload tab to submit a new file, then return here to
                    download the redacted version and generated audit reports.
                  </p>
                </div>
              </div>
            </TabPanel>

            <TabPanel value="upload">
              <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
                <aside className="rounded-3xl border border-cyan-300/20 bg-cyan-300/10 p-6">
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-100">
                    Upload Workflow
                  </p>
                  <h2 className="mt-4 text-2xl font-semibold text-white">
                    Scan a new file
                  </h2>
                  <p className="mt-3 text-sm leading-6 text-cyan-50/85">
                    Start a new redaction run here. Once processing completes,
                    the generated file and audit reports will appear in the
                    Redacted Files tab.
                  </p>

                  <div className="mt-6 space-y-4">
                    <div className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-300">
                        Step 1
                      </p>
                      <p className="mt-2 text-sm text-white">
                        Choose a supported file from your local machine.
                      </p>
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-300">
                        Step 2
                      </p>
                      <p className="mt-2 text-sm text-white">
                        Run the scan and wait for the risk analysis to complete.
                      </p>
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-300">
                        Step 3
                      </p>
                      <p className="mt-2 text-sm text-white">
                        Review the redacted output and download the audit
                        report.
                      </p>
                    </div>
                  </div>
                </aside>

                <div className="rounded-[2rem] border border-white/10 bg-slate-950/60 p-4 sm:p-6">
                  <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-5">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-300">
                        Upload Console
                      </p>
                      <p className="mt-2 text-sm text-slate-400">
                        Supported files can be scanned directly from this panel.
                      </p>
                    </div>
                    <span className="rounded-full border border-emerald-300/30 bg-emerald-300/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-emerald-100">
                      Ready for scan
                    </span>
                  </div>
                  <Upload />
                </div>
              </div>
            </TabPanel>
          </TabPanels>
        </Tabs>

        <section className="rounded-[2rem] border border-white/10 bg-slate-950/60 p-6">
          <AnimatedLandingHeader />
        </section>
      </div>
    </div>
  );
}

export default Dashboard;
