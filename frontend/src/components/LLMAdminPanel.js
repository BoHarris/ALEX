import { useState } from "react";
import {
  useLLMStatus,
  useLLMTaskHistory,
  updateLLMSettings,
  triggerLLMCompletion,
} from "../hooks/useLLMAdmin";
import { Button } from "./button";

function StatusCard({ label, value, error = false }) {
  const baseClass = "rounded-lg border p-4";
  const colorClass = error
    ? "border-rose-300/40 bg-rose-300/10 text-rose-700 dark:text-rose-100"
    : "border-cyan-300/40 bg-cyan-300/10 text-cyan-700 dark:text-cyan-100";

  return (
    <div className={`${baseClass} ${colorClass}`}>
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-app-muted">
        {label}
      </p>
      <p className="mt-2 text-lg font-semibold">{value || "—"}</p>
    </div>
  );
}

function StatusPanel({ companyId }) {
  const { status, loading, error, reload } = useLLMStatus(companyId, true);

  if (loading) {
    return (
      <div className="surface-card rounded-lg border p-6">
        <h4 className="font-medium text-app">LLM System Status</h4>
        <p className="mt-2 text-sm text-app-secondary">Loading status...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="surface-card rounded-lg border p-6">
        <h4 className="font-medium text-app">LLM System Status</h4>
        <p className="mt-2 text-sm text-rose-600">Error loading status</p>
        <button
          onClick={reload}
          className="mt-4 rounded border px-3 py-1 text-xs hover:bg-white/10"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!status) {
    return null;
  }

  return (
    <div className="surface-card rounded-lg border p-6">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium text-app">LLM System Status</h4>
          <p className="mt-1 text-sm text-app-secondary">
            Monitor LLM service configuration and performance.
          </p>
        </div>
        <button
          onClick={reload}
          className="rounded border px-3 py-1 text-xs hover:bg-white/10"
        >
          Refresh
        </button>
      </div>

      <div className="mt- grid gap-4 sm:grid-cols-2">
        <StatusCard
          label="Service Status"
          value={status.enabled ? "Enabled" : "Disabled"}
        />
        <StatusCard
          label="Model"
          value={status.model?.split("-")[1] || "N/A"}
        />
        <StatusCard label="Max Tokens" value={status.max_tokens} />
        <StatusCard label="Temperature" value={status.temperature} />
        <StatusCard
          label="Tasks Processed"
          value={status.tasks_with_llm_generation}
        />
        <StatusCard
          label="Avg Generation Time"
          value={
            status.avg_generation_time_seconds
              ? `${status.avg_generation_time_seconds.toFixed(2)}s`
              : "N/A"
          }
        />
      </div>

      {status.last_error && (
        <div className="border-rose-300/40 bg-rose-300/10 text-rose-700 mt-4 rounded-lg border p-4 dark:text-rose-100">
          <p className="text-xs font-semibold uppercase tracking-[0.24em]">
            Last Error
          </p>
          <p className="mt-2 text-sm">{status.last_error}</p>
        </div>
      )}
    </div>
  );
}

function SettingsPanel({ companyId }) {
  const [enabled, setEnabled] = useState(true);
  const [model, setModel] = useState("claude-3-5-sonnet-20241022");
  const [maxTokens, setMaxTokens] = useState(1024);
  const [temperature, setTemperature] = useState(0.7);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    try {
      await updateLLMSettings(companyId, {
        enabled,
        model,
        max_tokens: parseInt(maxTokens),
        temperature: parseFloat(temperature),
      });
      setMessage({ type: "success", text: "Settings updated successfully" });
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="surface-card rounded-lg border p-6">
      <h4 className="font-medium text-app">LLM Configuration</h4>
      <p className="mt-1 text-sm text-app-secondary">
        Adjust LLM parameters and settings.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-app">
            Service Status
          </label>
          <select
            value={enabled}
            onChange={(e) => setEnabled(e.target.value === "true")}
            className="background-input text-app mt-2 w-full rounded-lg border px-3 py-2 text-sm"
          >
            <option value="true">Enabled</option>
            <option value="false">Disabled</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-app">Model</label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="background-input text-app mt-2 w-full rounded-lg border px-3 py-2 text-sm"
          >
            <option value="claude-3-5-sonnet-20241022">
              Claude 3.5 Sonnet
            </option>
            <option value="claude-3-5-haiku-20241022">Claude 3.5 Haiku</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-app">
            Max Tokens ({maxTokens})
          </label>
          <input
            type="range"
            min="1"
            max="4096"
            value={maxTokens}
            onChange={(e) => setMaxTokens(e.target.value)}
            className="mt-2 w-full"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-app">
            Temperature ({temperature.toFixed(2)})
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={temperature}
            onChange={(e) => setTemperature(e.target.value)}
            className="mt-2 w-full"
          />
        </div>

        {message && (
          <div
            className={`rounded-lg border p-3 text-sm ${
              message.type === "success"
                ? "border-emerald-300/40 bg-emerald-300/10 text-emerald-700 dark:text-emerald-100"
                : "border-rose-300/40 bg-rose-300/10 text-rose-700 dark:text-rose-100"
            }`}
          >
            {message.text}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg border border-cyan-300/40 bg-cyan-300/10 px-4 py-2 font-medium text-cyan-700 hover:bg-cyan-300/20 disabled:opacity-50 dark:text-cyan-100"
        >
          {loading ? "Updating..." : "Save Settings"}
        </button>
      </form>
    </div>
  );
}

function TaskHistoryPanel({ companyId, taskId, onClose }) {
  const { history, loading, error, reload } = useLLMTaskHistory(
    companyId,
    taskId,
    true,
  );

  if (loading) {
    return (
      <div className="surface-card rounded-lg border p-6">
        <h4 className="font-medium text-app">Task History</h4>
        <p className="mt-2 text-sm text-app-secondary">Loading history...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="surface-card rounded-lg border p-6">
        <h4 className="font-medium text-app">Task History</h4>
        <p className="mt-2 text-sm text-rose-600">Error loading history</p>
        <button
          onClick={reload}
          className="mt-4 rounded border px-3 py-1 text-xs hover:bg-white/10"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!history || !history.generations || history.generations.length === 0) {
    return (
      <div className="surface-card rounded-lg border p-6">
        <h4 className="font-medium text-app">Task History</h4>
        <p className="mt-2 text-sm text-app-secondary">
          No LLM generations found for this task.
        </p>
      </div>
    );
  }

  return (
    <div className="surface-card rounded-lg border p-6">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium text-app">
            Task {history.task_id} History
          </h4>
          <p className="mt-1 text-sm text-app-secondary">
            LLM generation attempts for this task.
          </p>
        </div>
        <button
          onClick={onClose}
          className="rounded border px-3 py-1 text-xs hover:bg-white/10"
        >
          Close
        </button>
      </div>

      <div className="mt-4 space-y-3">
        {history.generations.map((gen, idx) => (
          <div
            key={idx}
            className={`rounded-lg border p-4 ${
              gen.status === "success"
                ? "border-emerald-300/40 bg-emerald-300/10"
                : "border-rose-300/40 bg-rose-300/10"
            }`}
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-semibold text-app">
                  {new Date(gen.timestamp).toLocaleString()}
                </p>
                <p className="mt-1 text-xs text-app-muted">{gen.model}</p>
              </div>
              <span
                className={`rounded-full px-2 py-1 text-xs font-semibold ${
                  gen.status === "success"
                    ? "bg-emerald-500/20 text-emerald-700 dark:text-emerald-100"
                    : "bg-rose-500/20 text-rose-700 dark:text-rose-100"
                }`}
              >
                {gen.status.toUpperCase()}
              </span>
            </div>
            {gen.error && (
              <p className="mt-2 text-xs text-rose-700 dark:text-rose-100">
                Error: {gen.error}
              </p>
            )}
            {gen.generated_fields && gen.generated_fields.length > 0 && (
              <p className="mt-2 text-xs text-app-secondary">
                Generated: {gen.generated_fields.join(", ")}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export function LLMAdminPanel({ companyId, isAdmin }) {
  const [view, setView] = useState("status"); // status, settings, history
  const [selectedTaskId, setSelectedTaskId] = useState(null);

  if (!isAdmin) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div className="surface-card p-6">
        <h3 className="text-lg font-semibold text-app">LLM Administration</h3>
        <p className="mt-1 text-sm text-app-secondary">
          Manage Large Language Model settings and monitor completion tasks.
        </p>

        <div className="mt-4 flex flex-wrap gap-2">
          <button
            onClick={() => setView("status")}
            className={`rounded-lg px-4 py-2 text-sm font-medium ${
              view === "status"
                ? "border-cyan-300/40 bg-cyan-300/10 text-cyan-700 dark:text-cyan-100"
                : "border border-app text-app hover:bg-white/10"
            }`}
          >
            Status
          </button>
          <button
            onClick={() => setView("settings")}
            className={`rounded-lg px-4 py-2 text-sm font-medium ${
              view === "settings"
                ? "border-cyan-300/40 bg-cyan-300/10 text-cyan-700 dark:text-cyan-100"
                : "border border-app text-app hover:bg-white/10"
            }`}
          >
            Settings
          </button>
          <button
            onClick={() => setView("history")}
            className={`rounded-lg px-4 py-2 text-sm font-medium ${
              view === "history"
                ? "border-cyan-300/40 bg-cyan-300/10 text-cyan-700 dark:text-cyan-100"
                : "border border-app text-app hover:bg-white/10"
            }`}
          >
            Task History
          </button>
        </div>
      </div>

      {view === "status" && <StatusPanel companyId={companyId} />}

      {view === "settings" && <SettingsPanel companyId={companyId} />}

      {view === "history" && (
        <div className="surface-card rounded-lg border p-6">
          <h4 className="font-medium text-app">View Task History</h4>
          <p className="mt-1 text-sm text-app-secondary">
            Enter a task ID to view its LLM generation history.
          </p>
          <div className="mt-4 flex gap-2">
            <input
              type="number"
              value={selectedTaskId || ""}
              onChange={(e) =>
                setSelectedTaskId(
                  e.target.value ? parseInt(e.target.value) : null,
                )
              }
              placeholder="Enter task ID"
              className="background-input text-app flex-1 rounded-lg border px-3 py-2 text-sm"
            />
            <button
              onClick={() => setView("history-detail")}
              disabled={!selectedTaskId}
              className="rounded-lg border border-cyan-300/40 bg-cyan-300/10 px-4 py-2 font-medium text-cyan-700 disabled:opacity-50 dark:text-cyan-100"
            >
              Search
            </button>
          </div>
        </div>
      )}

      {view === "history-detail" && selectedTaskId && (
        <TaskHistoryPanel
          companyId={companyId}
          taskId={selectedTaskId}
          onClose={() => setView("history")}
        />
      )}
    </div>
  );
}
