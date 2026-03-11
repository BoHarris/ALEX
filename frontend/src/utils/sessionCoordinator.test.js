import { waitFor } from "@testing-library/react";

const mockPublishAuthEvent = jest.fn();
const mockInvalidateCurrentUserCache = jest.fn();
let mockAuthEventHandler = null;

jest.mock("./authEvents", () => ({
  publishAuthEvent: (...args) => mockPublishAuthEvent(...args),
  subscribeToAuthEvents: (handler) => {
    mockAuthEventHandler = handler;
    return jest.fn();
  },
}));

jest.mock("./currentUserCache", () => ({
  invalidateCurrentUserCache: (...args) => mockInvalidateCurrentUserCache(...args),
}));

function createJsonResponse(ok, body) {
  return {
    ok,
    text: async () => JSON.stringify(body),
  };
}

describe("sessionCoordinator", () => {
  let coordinator;
  let tokenStore;

  beforeEach(() => {
    jest.resetModules();
    mockAuthEventHandler = null;
    mockPublishAuthEvent.mockReset();
    mockInvalidateCurrentUserCache.mockReset();
    global.fetch = jest.fn();

    coordinator = require("./sessionCoordinator");
    tokenStore = require("./tokenStore");
    coordinator.completeLogout({ broadcast: false });
  });

  afterEach(() => {
    delete global.fetch;
  });

  test("refresh recovery success restores authenticated state", async () => {
    fetch.mockResolvedValue(createJsonResponse(true, { access_token: "fresh-token" }));

    const recovered = await coordinator.recoverSession({
      failureMode: "expired",
      broadcastSuccess: true,
    });

    expect(recovered).toBe(true);
    expect(tokenStore.getAccessToken()).toBe("fresh-token");
    expect(coordinator.getSessionSnapshot()).toMatchObject({
      status: "authenticated",
    });
    expect(mockPublishAuthEvent).toHaveBeenCalledWith("auth:refresh_recovered");
  });

  test("refresh failure expires the session and clears auth state", async () => {
    coordinator.completeLogin("existing-token", { broadcast: false });
    fetch.mockResolvedValue(createJsonResponse(false, { detail: "expired" }));

    const recovered = await coordinator.recoverSession({
      failureMode: "expired",
    });

    expect(recovered).toBe(false);
    expect(tokenStore.getAccessToken()).toBeNull();
    expect(coordinator.getSessionSnapshot()).toMatchObject({
      status: "expired",
      message: "Session expired. Please sign in again.",
    });
    expect(mockPublishAuthEvent).toHaveBeenCalledWith("auth:session_expired");
  });

  test("cross-tab logout clears the current tab state", () => {
    coordinator.completeLogin("existing-token", { broadcast: false });
    coordinator.initializeSessionCoordinator();

    mockAuthEventHandler({ type: "auth:logout" });

    expect(tokenStore.getAccessToken()).toBeNull();
    expect(coordinator.getSessionSnapshot()).toMatchObject({
      status: "anonymous",
      message: "You were signed out in another tab.",
    });
  });

  test("cross-tab refresh recovery rehydrates the current tab", async () => {
    fetch.mockResolvedValue(createJsonResponse(true, { access_token: "recovered-token" }));
    coordinator.initializeSessionCoordinator();

    mockAuthEventHandler({ type: "auth:refresh_recovered" });

    await waitFor(() => {
      expect(tokenStore.getAccessToken()).toBe("recovered-token");
      expect(coordinator.getSessionSnapshot()).toMatchObject({
        status: "authenticated",
      });
    });
  });
});
