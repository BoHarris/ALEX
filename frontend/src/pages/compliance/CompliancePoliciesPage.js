import { useState } from "react";
import { Button } from "../../components/button";
import DetailDrawer from "../../components/compliance/DetailDrawer";
import WorkspaceEmptyState from "../../components/compliance/WorkspaceEmptyState";
import { useCompliancePageContext } from "./useCompliancePageContext";
import { formatDateTime, statusTone } from "./utils";

const categories = ["Security Policies", "Privacy Policies", "Operational Runbooks", "Vendor Procedures", "Incident Response", "Engineering Guidelines"];
const initialPolicy = { title: "", category: "Security Policies", content_markdown: "", tags: "", status: "draft" };

export default function CompliancePoliciesPage() {
  const workspace = useCompliancePageContext();
  const pages = workspace.data?.pages?.pages || [];
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedPage, setSelectedPage] = useState(null);
  const [form, setForm] = useState(initialPolicy);
  const [error, setError] = useState(null);

  const filteredPages = pages.filter((item) => {
    const matchesSearch = !search || item.record.title.toLowerCase().includes(search.toLowerCase());
    const matchesCategory = !categoryFilter || item.page.category === categoryFilter;
    const matchesStatus = !statusFilter || item.record.status === statusFilter;
    const matchesTag = !tagFilter || item.page.tags.some((tag) => tag.toLowerCase().includes(tagFilter.toLowerCase()));
    return matchesSearch && matchesCategory && matchesStatus && matchesTag;
  });

  async function openPage(item) {
    setSelectedPage(item);
    await workspace.loadRecordTimeline(item.record.id);
  }

  async function createPolicy(event) {
    event.preventDefault();
    setError(null);
    try {
      await workspace.createWikiPage({ ...form, tags: form.tags.split(",").map((item) => item.trim()).filter(Boolean) });
      setForm(initialPolicy);
      setCreateOpen(false);
    } catch (err) {
      setError(err.message);
    }
  }

  async function updatePolicy(payload) {
    if (!selectedPage) {
      return;
    }
    setError(null);
    try {
      await workspace.updateWikiPage(selectedPage.page.id, payload);
      setSelectedPage((current) => ({
        ...current,
        record: { ...current.record, ...("status" in payload ? { status: payload.status } : {}) },
        page: { ...current.page, ...("content_markdown" in payload ? { content_markdown: payload.content_markdown } : {}) },
      }));
    } catch (err) {
      setError(err.message);
    }
  }

  const timeline = selectedPage ? workspace.timelineCache[selectedPage.record.id]?.timeline : null;

  return (
    <div className="grid gap-6 xl:grid-cols-[260px_minmax(0,1fr)]">
      <aside className="surface-card rounded-3xl p-5">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-app">Categories</h2>
          <Button onClick={() => setCreateOpen(true)}>Create Policy</Button>
        </div>
        <div className="mt-4 space-y-2">
          <button type="button" onClick={() => setCategoryFilter("")} className={`w-full rounded-2xl px-3 py-2 text-left text-sm ${!categoryFilter ? "bg-cyan-500 text-slate-950" : "text-app-secondary hover:bg-white/5 hover:text-app"}`}>All categories</button>
          {categories.map((category) => (
            <button key={category} type="button" onClick={() => setCategoryFilter(category)} className={`w-full rounded-2xl px-3 py-2 text-left text-sm ${categoryFilter === category ? "bg-cyan-500 text-slate-950" : "text-app-secondary hover:bg-white/5 hover:text-app"}`}>{category}</button>
          ))}
        </div>
      </aside>

      <section className="space-y-6">
        <div className="surface-card rounded-3xl p-6">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
            <div>
              <h2 className="text-2xl font-semibold text-app">Policies</h2>
              <p className="mt-2 text-sm text-app-secondary">Internal wiki, runbooks, and policy pages with versioned records.</p>
            </div>
            <div className="flex flex-wrap gap-3">
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search policies" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
              <input value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} placeholder="Filter status" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
              <input value={tagFilter} onChange={(event) => setTagFilter(event.target.value)} placeholder="Filter tag" className="rounded-xl border border-app bg-app px-3 py-2 text-sm text-app" />
            </div>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {filteredPages.length ? filteredPages.map((item) => (
            <button key={item.page.id} type="button" onClick={() => openPage(item)} className="surface-card rounded-3xl p-5 text-left hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300">
              <p className="text-lg font-semibold text-app">{item.record.title}</p>
              <p className="mt-2 text-sm text-app-secondary">{item.page.category} · v{item.page.version}</p>
              <p className={`mt-2 text-sm font-medium ${statusTone(item.record.status)}`}>{item.record.status}</p>
              <p className="mt-3 text-xs text-app-muted">{formatDateTime(item.record.updated_at)}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {item.page.tags.map((tag) => <span key={tag} className="rounded-full border border-app px-2 py-1 text-xs text-app-secondary">{tag}</span>)}
              </div>
            </button>
          )) : <WorkspaceEmptyState title="No policy pages match" description="Adjust filters or create a new policy page." action={<Button onClick={() => setCreateOpen(true)}>Create Policy</Button>} />}
        </div>
      </section>

      <DetailDrawer open={createOpen} onClose={() => setCreateOpen(false)} title="Create Policy Page" subtitle="Use a drawer for policy authoring instead of placing forms above the list.">
        <form className="space-y-4" onSubmit={createPolicy}>
          <label className="block text-sm text-app-secondary">Title<input required value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="block text-sm text-app-secondary">Category<select value={form.category} onChange={(event) => setForm((current) => ({ ...current, category: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app">{categories.map((category) => <option key={category} value={category}>{category}</option>)}</select></label>
          <label className="block text-sm text-app-secondary">Status<input value={form.status} onChange={(event) => setForm((current) => ({ ...current, status: event.target.value }))} className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="block text-sm text-app-secondary">Tags<input value={form.tags} onChange={(event) => setForm((current) => ({ ...current, tags: event.target.value }))} placeholder="incident, runbook" className="mt-2 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          <label className="block text-sm text-app-secondary">Content<textarea value={form.content_markdown} onChange={(event) => setForm((current) => ({ ...current, content_markdown: event.target.value }))} className="mt-2 min-h-48 w-full rounded-xl border border-app bg-app px-3 py-2 text-app" /></label>
          {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          <Button type="submit">Create Policy</Button>
        </form>
      </DetailDrawer>

      <DetailDrawer
        open={Boolean(selectedPage)}
        onClose={() => setSelectedPage(null)}
        title={selectedPage?.record.title || "Policy Detail"}
        subtitle={selectedPage ? `${selectedPage.page.category} · v${selectedPage.page.version} · ${selectedPage.record.status}` : ""}
      >
        {selectedPage ? (
          <>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Content</h3>
              <pre className="mt-4 whitespace-pre-wrap text-sm leading-7 text-app-secondary">{selectedPage.page.content_markdown || "No policy content yet."}</pre>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Actions</h3>
              <div className="mt-4 flex flex-wrap gap-3">
                <Button onClick={() => updatePolicy({ status: selectedPage.record.status === "published" ? "draft" : "published" })}>{selectedPage.record.status === "published" ? "Unpublish" : "Publish"}</Button>
                <Button onClick={() => updatePolicy({ status: selectedPage.record.status === "archived" ? "draft" : "archived" })}>{selectedPage.record.status === "archived" ? "Restore" : "Archive"}</Button>
                <Button onClick={() => updatePolicy({ content_markdown: `${selectedPage.page.content_markdown}\n\nDuplicate reference prepared.` })}>Duplicate</Button>
              </div>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">History</h3>
              <div className="mt-4 space-y-3">
                {timeline?.activities?.length ? timeline.activities.map((item) => (
                  <div key={item.id} className="rounded-2xl border border-app p-4 text-sm text-app-secondary">
                    <p className="font-semibold text-app">{item.action}</p>
                    <p className="mt-1">{item.details || "No details"}</p>
                  </div>
                )) : <p className="text-sm text-app-muted">No timeline activity yet.</p>}
              </div>
            </section>
            <section className="surface-card rounded-3xl p-5">
              <h3 className="text-lg font-semibold text-app">Training Links</h3>
              <p className="mt-4 text-sm text-app-secondary">Generated training documents are stored in the same wiki workspace and can be cross-linked from procedures like this one.</p>
            </section>
            {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          </>
        ) : null}
      </DetailDrawer>
    </div>
  );
}
