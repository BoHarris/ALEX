import { bootstrapSession, recoverSession } from "./sessionCoordinator";

export async function rehydrateSession() {
  return bootstrapSession();
}

export async function refreshSessionOrExpire() {
  return recoverSession({
    failureMode: "expired",
    broadcastSuccess: true,
  });
}
