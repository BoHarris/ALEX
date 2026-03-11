let accessToken = null;
const listeners = new Set();

function emitTokenChange() {
  listeners.forEach((listener) => listener(accessToken));
}

export function getAccessToken() {
  return accessToken;
}

export function setAccessToken(token) {
  accessToken = token || null;
  emitTokenChange();
}

export function clearAccessToken() {
  accessToken = null;
  emitTokenChange();
}

export function subscribeToAccessToken(listener) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
