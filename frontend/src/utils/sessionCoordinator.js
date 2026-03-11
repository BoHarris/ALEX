import { useSyncExternalStore } from "react";
import { apiUrl } from "./api";
import { publishAuthEvent, subscribeToAuthEvents } from "./authEvents";
import { invalidateCurrentUserCache } from "./currentUserCache";
import { readResponseData } from "./http";
import { clearAccessToken, getAccessToken, setAccessToken } from "./tokenStore";

const SESSION_MESSAGE = {
  loginSuccess: "Signed in successfully.",
  registrationComplete: "Registration complete. Your passkey is ready. Please sign in to continue.",
  sessionExpired: "Session expired. Please sign in again.",
  signedOutElsewhere: "You were signed out in another tab.",
};

const sessionListeners = new Set();

let sessionState = {
  status: "loading",
  message: null,
  messageTone: "info",
};
let syncTeardown = null;
let activeRecoveryPromise = null;

function emitSessionChange() {
  sessionListeners.forEach((listener) => listener());
}

function updateSessionState(nextState) {
  sessionState = {
    ...sessionState,
    ...nextState,
  };
  emitSessionChange();
}

function setAuthenticatedState(token, message = null, options = {}) {
  if (!token) {
    return false;
  }

  setAccessToken(token);
  invalidateCurrentUserCache();
  updateSessionState({
    status: "authenticated",
    message,
    messageTone: options.messageTone || "success",
  });

  if (options.eventType) {
    publishAuthEvent(options.eventType);
  }

  return true;
}

function clearSessionState(status, message, options = {}) {
  clearAccessToken();
  invalidateCurrentUserCache();
  updateSessionState({
    status,
    message,
    messageTone: options.messageTone || "info",
  });

  if (options.eventType) {
    publishAuthEvent(options.eventType);
  }
}

async function requestSessionRefresh() {
  const response = await fetch(apiUrl("/auth/refresh"), {
    method: "POST",
    credentials: "include",
  });

  if (!response.ok) {
    return null;
  }

  const { data } = await readResponseData(response);
  return data?.access_token || null;
}

export function getSessionSnapshot() {
  return sessionState;
}

export function subscribeToSession(listener) {
  sessionListeners.add(listener);
  return () => {
    sessionListeners.delete(listener);
  };
}

export function useSessionState() {
  return useSyncExternalStore(subscribeToSession, getSessionSnapshot, getSessionSnapshot);
}

export async function recoverSession(options = {}) {
  const {
    failureMode = "expired",
    broadcastSuccess = false,
    successMessage = null,
    loading = false,
  } = options;

  if (activeRecoveryPromise) {
    return activeRecoveryPromise;
  }

  if (loading) {
    updateSessionState({
      status: "loading",
      message: sessionState.status === "authenticated" ? sessionState.message : null,
      messageTone: sessionState.messageTone,
    });
  }

  activeRecoveryPromise = (async () => {
    try {
      const accessToken = await requestSessionRefresh();
      if (!accessToken) {
        if (failureMode === "anonymous") {
          clearSessionState("anonymous", null);
        } else {
          clearSessionState("expired", SESSION_MESSAGE.sessionExpired, {
            eventType: "auth:session_expired",
            messageTone: "warning",
          });
        }
        return false;
      }

      setAuthenticatedState(accessToken, successMessage, {
        eventType: broadcastSuccess ? "auth:refresh_recovered" : null,
        messageTone: successMessage ? "success" : "info",
      });
      return true;
    } catch {
      if (failureMode === "anonymous") {
        clearSessionState("anonymous", null);
      } else {
        clearSessionState("expired", SESSION_MESSAGE.sessionExpired, {
          eventType: "auth:session_expired",
          messageTone: "warning",
        });
      }
      return false;
    } finally {
      activeRecoveryPromise = null;
    }
  })();

  return activeRecoveryPromise;
}

export async function bootstrapSession() {
  if (getAccessToken()) {
    updateSessionState({
      status: "authenticated",
      message: sessionState.message,
      messageTone: sessionState.messageTone,
    });
    return true;
  }

  return recoverSession({
    failureMode: "anonymous",
    loading: true,
  });
}

export function completeLogin(accessToken, options = {}) {
  return setAuthenticatedState(accessToken, options.message || SESSION_MESSAGE.loginSuccess, {
    eventType: options.broadcast === false ? null : "auth:login",
    messageTone: "success",
  });
}

export function completeLogout(options = {}) {
  clearSessionState("anonymous", options.message || null, {
    eventType: options.broadcast === false ? null : "auth:logout",
    messageTone: "info",
  });
}

export function expireSession(options = {}) {
  clearSessionState("expired", options.message || SESSION_MESSAGE.sessionExpired, {
    eventType: options.broadcast === false ? null : "auth:session_expired",
    messageTone: "warning",
  });
}

export function getRegistrationCompletionMessage() {
  return SESSION_MESSAGE.registrationComplete;
}

export function consumeSessionMessage() {
  if (!sessionState.message) {
    return;
  }

  updateSessionState({
    message: null,
    messageTone: "info",
  });
}

export function initializeSessionCoordinator() {
  if (syncTeardown) {
    return syncTeardown;
  }

  syncTeardown = subscribeToAuthEvents((event) => {
    switch (event.type) {
      case "auth:login":
        void recoverSession({
          failureMode: "anonymous",
          successMessage: SESSION_MESSAGE.loginSuccess,
        });
        break;
      case "auth:refresh_recovered":
        void recoverSession({
          failureMode: "anonymous",
        });
        break;
      case "auth:logout":
        completeLogout({
          message: SESSION_MESSAGE.signedOutElsewhere,
          broadcast: false,
        });
        break;
      case "auth:session_expired":
        expireSession({
          message: SESSION_MESSAGE.sessionExpired,
          broadcast: false,
        });
        break;
      default:
        break;
    }
  });

  return () => {
    if (syncTeardown) {
      syncTeardown();
      syncTeardown = null;
    }
  };
}
