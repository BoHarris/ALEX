const AUTH_EVENT_STORAGE_KEY = "alex.auth.event";
const TAB_ID = `tab-${Math.random().toString(36).slice(2)}-${Date.now()}`;

let broadcastChannel = null;

function getBroadcastChannel() {
  if (typeof window === "undefined" || typeof window.BroadcastChannel === "undefined") {
    return null;
  }

  if (!broadcastChannel) {
    broadcastChannel = new window.BroadcastChannel("alex-auth");
  }

  return broadcastChannel;
}

function parseEventPayload(rawValue) {
  if (!rawValue) {
    return null;
  }

  try {
    return JSON.parse(rawValue);
  } catch {
    return null;
  }
}

export function publishAuthEvent(type, payload = {}) {
  if (typeof window === "undefined") {
    return;
  }

  const event = {
    type,
    payload,
    senderId: TAB_ID,
    emittedAt: Date.now(),
  };

  const channel = getBroadcastChannel();
  if (channel) {
    channel.postMessage(event);
    return;
  }

  const serialized = JSON.stringify(event);
  window.localStorage.setItem(AUTH_EVENT_STORAGE_KEY, serialized);
  window.localStorage.removeItem(AUTH_EVENT_STORAGE_KEY);
}

export function subscribeToAuthEvents(listener) {
  if (typeof window === "undefined") {
    return () => {};
  }

  const handleEvent = (event) => {
    if (!event || event.senderId === TAB_ID || !event.type) {
      return;
    }
    listener(event);
  };

  const channel = getBroadcastChannel();
  const handleChannelMessage = (messageEvent) => {
    handleEvent(messageEvent.data);
  };
  const handleStorageEvent = (storageEvent) => {
    if (storageEvent.key !== AUTH_EVENT_STORAGE_KEY) {
      return;
    }
    handleEvent(parseEventPayload(storageEvent.newValue));
  };

  if (channel) {
    channel.addEventListener("message", handleChannelMessage);
  }
  window.addEventListener("storage", handleStorageEvent);

  return () => {
    if (channel) {
      channel.removeEventListener("message", handleChannelMessage);
    }
    window.removeEventListener("storage", handleStorageEvent);
  };
}
