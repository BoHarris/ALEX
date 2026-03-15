import { useCallback, useEffect, useState } from "react";
import { authFetch } from "../utils/authFetch";
import { getResponseMessage, readResponseData } from "../utils/http";

export async function requestComplianceJson(path, options = {}) {
  const response = await authFetch(path, options);
  const { data, text } = await readResponseData(response);
  if (!response.ok) {
    throw new Error(getResponseMessage(data, `Unable to load ${path}`, text));
  }
  return data;
}

function buildTestIdQuery(caseId) {
  return `?test_id=${encodeURIComponent(caseId)}`;
}

export function useComplianceWorkspace(enabled = true) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [testCategoryDetail, setTestCategoryDetail] = useState(null);
  const [selectedTestCase, setSelectedTestCase] = useState(null);
  const [testDashboard, setTestDashboard] = useState(null);
  const [selectedTestRun, setSelectedTestRun] = useState(null);
  const [timelineCache, setTimelineCache] = useState({});
  const [selectedTaskDetail, setSelectedTaskDetail] = useState(null);

  const loadWorkspace = useCallback(async () => {
    const [
      me,
      overview,
      directory,
      pages,
      vendors,
      incidents,
      tasks,
      automation,
      taskSummary,
      risks,
      reviews,
      assignments,
      tests,
      testRuns,
      modules,
      auditLog,
      codeReviews,
    ] = await Promise.all([
      requestComplianceJson("/compliance/me"),
      requestComplianceJson("/compliance/overview"),
      requestComplianceJson("/compliance/directory"),
      requestComplianceJson("/compliance/wiki/pages"),
      requestComplianceJson("/compliance/vendors"),
      requestComplianceJson("/compliance/incidents"),
      requestComplianceJson("/compliance/tasks"),
      requestComplianceJson("/compliance/automation/tasks"),
      requestComplianceJson("/compliance/tasks/summary"),
      requestComplianceJson("/compliance/risks"),
      requestComplianceJson("/compliance/access-reviews"),
      requestComplianceJson("/compliance/training/assignments"),
      requestComplianceJson("/compliance/tests/dashboard"),
      requestComplianceJson("/compliance/tests/runs?limit=12"),
      requestComplianceJson("/compliance/training/modules"),
      requestComplianceJson("/compliance/audit-log"),
      requestComplianceJson("/compliance/code-reviews"),
    ]);
    return {
      me,
      overview,
      directory,
      pages,
      vendors,
      incidents,
      tasks,
      automation,
      taskSummary,
      risks,
      reviews,
      assignments,
      tests,
      testRuns,
      modules,
      auditLog,
      codeReviews,
    };
  }, []);

  useEffect(() => {
    if (!enabled) {
      setData(null);
      setLoading(false);
      setError(null);
      return;
    }
    let mounted = true;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const nextData = await loadWorkspace();
        if (mounted) {
          setData(nextData);
          setTestDashboard(nextData.tests || null);
        }
      } catch (err) {
        if (mounted) {
          setError(err);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }
    load();
    return () => {
      mounted = false;
    };
  }, [enabled, loadWorkspace, reloadKey]);

  const mutateAndReturn = useCallback(
    async (path, body, method = "POST") => {
      const payload = await requestComplianceJson(path, {
        method,
        headers: { "Content-Type": "application/json" },
        body: body != null ? JSON.stringify(body) : undefined,
      });
      const nextData = await loadWorkspace();
      setData(nextData);
      return { payload, nextData };
    },
    [loadWorkspace],
  );

  const mutate = useCallback(
    async (path, body, method = "POST") => {
      const { nextData } = await mutateAndReturn(path, body, method);
      return nextData;
    },
    [mutateAndReturn],
  );

  const loadTestInventory = useCallback(async (filters = {}) => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value != null && value !== "") {
        params.set(key, value);
      }
    });
    const suffix = params.toString() ? `?${params.toString()}` : "";
    return requestComplianceJson(`/compliance/tests/inventory${suffix}`);
  }, []);

  const loadTestCase = useCallback(async (caseId) => {
    const [detail, history] = await Promise.all([
      requestComplianceJson(
        `/compliance/tests/case-detail${buildTestIdQuery(caseId)}`,
      ),
      requestComplianceJson(
        `/compliance/tests/case-history${buildTestIdQuery(caseId)}`,
      ),
    ]);
    const nextDetail = { ...detail, history: history.history || [] };
    setSelectedTestCase(nextDetail);
    return nextDetail;
  }, []);

  const loadTestRuns = useCallback(async (filters = {}) => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value != null && value !== "") {
        params.set(key, String(value));
      }
    });
    const suffix = params.toString() ? `?${params.toString()}` : "";
    const payload = await requestComplianceJson(
      `/compliance/tests/runs${suffix}`,
    );
    setData((current) =>
      current ? { ...current, testRuns: payload } : current,
    );
    return payload;
  }, []);

  const loadTestRunDetail = useCallback(async (runId) => {
    const payload = await requestComplianceJson(
      `/compliance/tests/runs/${runId}`,
    );
    setSelectedTestRun(payload);
    return payload;
  }, []);

  const createOrAssignTestTask = useCallback(
    async (caseId, payload = {}) => {
      await requestComplianceJson(
        `/compliance/tests/case-task${buildTestIdQuery(caseId)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      return loadTestCase(caseId);
    },
    [loadTestCase],
  );

  const updateTestTask = useCallback(
    async (taskId, payload = {}) => {
      await requestComplianceJson(`/compliance/tests/tasks/${taskId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (selectedTestCase?.test_id) {
        return loadTestCase(selectedTestCase.test_id);
      }
      return null;
    },
    [loadTestCase, selectedTestCase?.test_id],
  );

  const loadTestDashboard = useCallback(async () => {
    const dashboard = await requestComplianceJson(
      "/compliance/tests/dashboard",
    );
    setTestDashboard(dashboard);
    setData((current) =>
      current ? { ...current, tests: dashboard } : current,
    );
    return dashboard;
  }, []);

  const loadTestCategory = useCallback(
    async (categoryName, options = {}) => {
      const inventory = await loadTestInventory({
        category: categoryName,
        ...options,
      });
      const detail = {
        category: categoryName,
        summary: inventory.summary,
        tests: inventory.tests,
      };
      setTestCategoryDetail(detail);
      if (!options.keepSelection) {
        setSelectedTestCase(null);
      }
      return detail;
    },
    [loadTestInventory],
  );

  const refreshTestingWorkspace = useCallback(async () => {
    const [dashboard, categoryDetail, runs] = await Promise.all([
      loadTestDashboard(),
      testCategoryDetail?.category
        ? loadTestCategory(testCategoryDetail.category)
        : Promise.resolve(null),
      loadTestRuns({ limit: 12 }),
    ]);
    if (selectedTestCase?.test_id) {
      await loadTestCase(selectedTestCase.test_id);
    }
    if (selectedTestRun?.run?.id) {
      await loadTestRunDetail(selectedTestRun.run.id);
    }
    return { dashboard, categoryDetail, runs };
  }, [
    loadTestCase,
    loadTestCategory,
    loadTestDashboard,
    loadTestRunDetail,
    loadTestRuns,
    selectedTestCase?.test_id,
    selectedTestRun?.run?.id,
    testCategoryDetail?.category,
  ]);

  const loadRecordTimeline = useCallback(
    async (recordId) => {
      if (timelineCache[recordId]) {
        return timelineCache[recordId];
      }
      const detail = await requestComplianceJson(
        `/compliance/records/${recordId}/timeline`,
      );
      setTimelineCache((current) => ({ ...current, [recordId]: detail }));
      return detail;
    },
    [timelineCache],
  );

  const loadTaskDetail = useCallback(async (taskId) => {
    const detail = await requestComplianceJson(`/compliance/tasks/${taskId}`);
    setSelectedTaskDetail(detail.task || null);
    return detail.task || null;
  }, []);

  const triggerTestRun = useCallback(
    async (path) => {
      const payload = await requestComplianceJson(path, { method: "POST" });
      const nextData = await loadWorkspace();
      setData(nextData);
      setTestDashboard(nextData.tests || null);
      if (payload?.run?.id) {
        await loadTestRunDetail(payload.run.id);
      }
      if (selectedTestCase?.test_id) {
        await loadTestCase(selectedTestCase.test_id);
      }
      return payload;
    },
    [loadTestCase, loadTestRunDetail, loadWorkspace, selectedTestCase?.test_id],
  );

  const createTaskFromSecurityIncident = useCallback(async (incidentId) => {
    const payload = await requestComplianceJson(
      `/compliance/tasks/from/security-incident/${incidentId}`,
      {
        method: "POST",
      },
    );
    return payload;
  }, []);

  const createTaskFromSecurityState = useCallback(async (stateId) => {
    const payload = await requestComplianceJson(
      `/compliance/tasks/from/security-state/${stateId}`,
      {
        method: "POST",
      },
    );
    return payload;
  }, []);

  return {
    data,
    loading,
    error,
    testDashboard,
    testCategoryDetail,
    selectedTestCase,
    selectedTestRun,
    selectedTaskDetail,
    timelineCache,
    clearTestDetail: () => {
      setTestCategoryDetail(null);
      setSelectedTestCase(null);
    },
    clearTestRunDetail: () => setSelectedTestRun(null),
    clearTaskDetail: () => setSelectedTaskDetail(null),
    loadTestCategory,
    loadTestDashboard,
    loadTestInventory,
    loadTestCase,
    loadTestRuns,
    loadTestRunDetail,
    createOrAssignTestTask,
    updateTestTask,
    runFullTestSuite: () => triggerTestRun("/compliance/tests/run-all"),
    runTestCase: (caseId) =>
      triggerTestRun(`/compliance/tests/run-test${buildTestIdQuery(caseId)}`),
    runTestCategory: (categoryName) =>
      triggerTestRun(
        `/compliance/tests/categories/${encodeURIComponent(categoryName)}/run`,
      ),
    refreshTestingWorkspace,
    loadRecordTimeline,
    loadTaskDetail,
    createEmployee: (payload) => mutate("/compliance/directory", payload),
    updateEmployee: (employeeId, payload) =>
      mutate(`/compliance/directory/${employeeId}`, payload, "PUT"),
    deactivateEmployee: (employeeId) =>
      mutate(`/compliance/directory/${employeeId}/deactivate`, null),
    createWikiPage: (payload) => mutate("/compliance/wiki/pages", payload),
    updateWikiPage: (wikiId, payload) =>
      mutate(`/compliance/wiki/pages/${wikiId}`, payload, "PUT"),
    createVendor: (payload) => mutate("/compliance/vendors", payload),
    updateVendor: (vendorId, payload) =>
      mutate(`/compliance/vendors/${vendorId}`, payload, "PUT"),
    createIncident: (payload) => mutate("/compliance/incidents", payload),
    updateIncident: (incidentId, payload) =>
      mutate(`/compliance/incidents/${incidentId}`, payload, "PUT"),
    createTask: (payload) => mutate("/compliance/tasks", payload),
    updateTask: (taskId, payload) =>
      mutate(`/compliance/tasks/${taskId}`, payload, "PATCH"),
    assignTask: (taskId, payload) =>
      mutate(`/compliance/tasks/${taskId}/assign`, payload),
    updateTaskStatus: (taskId, payload) =>
      mutate(`/compliance/tasks/${taskId}/status`, payload),
    linkTaskIncident: (taskId, payload) =>
      mutate(`/compliance/tasks/${taskId}/link-incident`, payload),
    linkTaskSource: (taskId, payload) =>
      mutate(`/compliance/tasks/${taskId}/link-source`, payload),
    createTaskFromIncident: (incidentId, payload) =>
      mutate(`/compliance/tasks/from/incident/${incidentId}`, payload),
    createTaskFromVendor: (vendorId, payload) =>
      mutate(`/compliance/tasks/from/vendor/${vendorId}`, payload),
    createTaskFromTestFailure: (testId, payload) =>
      mutate(
        `/compliance/tasks/from/test-failure${buildTestIdQuery(testId)}`,
        payload,
      ),
    createTaskFromEmployee: (employeeId, payload) =>
      mutate(`/compliance/tasks/from/employee/${employeeId}`, payload),
    syncAutomationBacklog: () =>
      mutateAndReturn("/compliance/automation/sync-backlog", null),
    startNextAutomationTask: () =>
      mutateAndReturn("/compliance/automation/tasks/start-next", null),
    assignTaskToAutomation: (taskId) =>
      mutateAndReturn(`/compliance/automation/tasks/${taskId}/assign`, null),
    startAutomationTask: (taskId) =>
      mutateAndReturn(`/compliance/automation/tasks/${taskId}/start`, null),
    completeAutomationTask: (taskId, payload) =>
      mutateAndReturn(`/compliance/automation/tasks/${taskId}/complete`, payload),
    failAutomationTask: (taskId, payload) =>
      mutateAndReturn(`/compliance/automation/tasks/${taskId}/fail`, payload),
    blockAutomationTask: (taskId, payload) =>
      mutateAndReturn(`/compliance/automation/tasks/${taskId}/block`, payload),
    markAutomationTaskReadyForReview: (taskId, payload) =>
      mutateAndReturn(`/compliance/automation/tasks/${taskId}/ready-for-review`, payload),
    returnAutomationTaskToBacklog: (taskId, payload) =>
      mutateAndReturn(`/compliance/automation/tasks/${taskId}/return-to-backlog`, payload),
    updateAutomationTaskMetadata: (taskId, payload) =>
      mutateAndReturn(`/compliance/automation/tasks/${taskId}/metadata`, payload, "PATCH"),
    createRisk: (payload) => mutate("/compliance/risks", payload),
    updateRisk: (riskId, payload) =>
      mutate(`/compliance/risks/${riskId}`, payload, "PUT"),
    createAccessReview: (payload) =>
      mutate("/compliance/access-reviews", payload),
    decideAccessReview: (reviewId, payload) =>
      mutate(`/compliance/access-reviews/${reviewId}/decision`, payload),
    createTrainingModule: (payload) =>
      mutate("/compliance/training/modules", payload),
    assignTraining: (payload) =>
      mutate("/compliance/training/assignments", payload),
    completeTraining: (assignmentId, payload) =>
      mutate(
        `/compliance/training/assignments/${assignmentId}/complete`,
        payload,
      ),
    createCodeReview: (payload) => mutate("/compliance/code-reviews", payload),
    updateCodeReview: (reviewId, payload) =>
      mutate(`/compliance/code-reviews/${reviewId}`, payload, "PUT"),
    decideCodeReview: (reviewId, payload) =>
      mutate(`/compliance/code-reviews/${reviewId}/decision`, payload),
    reload: async () => {
      setReloadKey((value) => value + 1);
    },
  };
}
