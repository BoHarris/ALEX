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

export function useComplianceWorkspace(enabled = true) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [testCategoryDetail, setTestCategoryDetail] = useState(null);
  const [selectedTestCase, setSelectedTestCase] = useState(null);
  const [testDashboard, setTestDashboard] = useState(null);
  const [timelineCache, setTimelineCache] = useState({});

  const loadWorkspace = useCallback(async () => {
    const [me, overview, directory, pages, vendors, incidents, risks, reviews, assignments, tests, modules, auditLog, codeReviews] = await Promise.all([
      requestComplianceJson("/compliance/me"),
      requestComplianceJson("/compliance/overview"),
      requestComplianceJson("/compliance/directory"),
      requestComplianceJson("/compliance/wiki/pages"),
      requestComplianceJson("/compliance/vendors"),
      requestComplianceJson("/compliance/incidents"),
      requestComplianceJson("/compliance/risks"),
      requestComplianceJson("/compliance/access-reviews"),
      requestComplianceJson("/compliance/training/assignments"),
      requestComplianceJson("/compliance/tests/dashboard"),
      requestComplianceJson("/compliance/training/modules"),
      requestComplianceJson("/compliance/audit-log"),
      requestComplianceJson("/compliance/code-reviews"),
    ]);
    return { me, overview, directory, pages, vendors, incidents, risks, reviews, assignments, tests, modules, auditLog, codeReviews };
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

  const mutate = useCallback(async (path, body, method = "POST") => {
    await requestComplianceJson(path, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body != null ? JSON.stringify(body) : undefined,
    });
    const nextData = await loadWorkspace();
    setData(nextData);
    return nextData;
  }, [loadWorkspace]);

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
      requestComplianceJson(`/compliance/tests/cases/${encodeURIComponent(caseId)}`),
      requestComplianceJson(`/compliance/tests/cases/${encodeURIComponent(caseId)}/history`),
    ]);
    const nextDetail = { ...detail, history: history.history || [] };
    setSelectedTestCase(nextDetail);
    return nextDetail;
  }, []);

  const createOrAssignTestTask = useCallback(async (caseId, payload = {}) => {
    await requestComplianceJson(`/compliance/tests/cases/${encodeURIComponent(caseId)}/task`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return loadTestCase(caseId);
  }, [loadTestCase]);

  const updateTestTask = useCallback(async (taskId, payload = {}) => {
    await requestComplianceJson(`/compliance/tests/tasks/${taskId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (selectedTestCase?.test_id) {
      return loadTestCase(selectedTestCase.test_id);
    }
    return null;
  }, [loadTestCase, selectedTestCase?.test_id]);

  const loadTestDashboard = useCallback(async () => {
    const dashboard = await requestComplianceJson("/compliance/tests/dashboard");
    setTestDashboard(dashboard);
    return dashboard;
  }, []);

  const loadTestCategory = useCallback(async (categoryName, options = {}) => {
    const inventory = await loadTestInventory({ category: categoryName, ...options });
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
  }, [loadTestInventory]);

  const refreshTestingWorkspace = useCallback(async () => {
    const [dashboard, categoryDetail] = await Promise.all([
      loadTestDashboard(),
      testCategoryDetail?.category ? loadTestCategory(testCategoryDetail.category) : Promise.resolve(null),
    ]);
    if (selectedTestCase?.test_id) {
      await loadTestCase(selectedTestCase.test_id);
    }
    return { dashboard, categoryDetail };
  }, [loadTestCase, loadTestCategory, loadTestDashboard, selectedTestCase?.test_id, testCategoryDetail?.category]);

  const loadRecordTimeline = useCallback(async (recordId) => {
    if (timelineCache[recordId]) {
      return timelineCache[recordId];
    }
    const detail = await requestComplianceJson(`/compliance/records/${recordId}/timeline`);
    setTimelineCache((current) => ({ ...current, [recordId]: detail }));
    return detail;
  }, [timelineCache]);

  return {
    data,
    loading,
    error,
    testDashboard,
    testCategoryDetail,
    selectedTestCase,
    timelineCache,
    clearTestDetail: () => {
      setTestCategoryDetail(null);
      setSelectedTestCase(null);
    },
    loadTestCategory,
    loadTestDashboard,
    loadTestInventory,
    loadTestCase,
    createOrAssignTestTask,
    updateTestTask,
    refreshTestingWorkspace,
    loadRecordTimeline,
    createEmployee: (payload) => mutate("/compliance/directory", payload),
    updateEmployee: (employeeId, payload) => mutate(`/compliance/directory/${employeeId}`, payload, "PUT"),
    deactivateEmployee: (employeeId) => mutate(`/compliance/directory/${employeeId}/deactivate`, null),
    createWikiPage: (payload) => mutate("/compliance/wiki/pages", payload),
    updateWikiPage: (wikiId, payload) => mutate(`/compliance/wiki/pages/${wikiId}`, payload, "PUT"),
    createVendor: (payload) => mutate("/compliance/vendors", payload),
    updateVendor: (vendorId, payload) => mutate(`/compliance/vendors/${vendorId}`, payload, "PUT"),
    createIncident: (payload) => mutate("/compliance/incidents", payload),
    updateIncident: (incidentId, payload) => mutate(`/compliance/incidents/${incidentId}`, payload, "PUT"),
    createRisk: (payload) => mutate("/compliance/risks", payload),
    updateRisk: (riskId, payload) => mutate(`/compliance/risks/${riskId}`, payload, "PUT"),
    createAccessReview: (payload) => mutate("/compliance/access-reviews", payload),
    decideAccessReview: (reviewId, payload) => mutate(`/compliance/access-reviews/${reviewId}/decision`, payload),
    createTrainingModule: (payload) => mutate("/compliance/training/modules", payload),
    assignTraining: (payload) => mutate("/compliance/training/assignments", payload),
    completeTraining: (assignmentId, payload) => mutate(`/compliance/training/assignments/${assignmentId}/complete`, payload),
    createCodeReview: (payload) => mutate("/compliance/code-reviews", payload),
    updateCodeReview: (reviewId, payload) => mutate(`/compliance/code-reviews/${reviewId}`, payload, "PUT"),
    decideCodeReview: (reviewId, payload) => mutate(`/compliance/code-reviews/${reviewId}/decision`, payload),
    reload: async () => {
      setReloadKey((value) => value + 1);
    },
  };
}
