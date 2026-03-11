let cachedUser = null;
let cachedUserPromise = null;
let cacheInitialized = false;

export function getCachedUser() {
  return cachedUser;
}

export function getCachedUserPromise() {
  return cachedUserPromise;
}

export function isCurrentUserCacheInitialized() {
  return cacheInitialized;
}

export function setCachedUser(user) {
  cachedUser = user;
  cacheInitialized = true;
}

export function setCachedUserPromise(promise) {
  cachedUserPromise = promise;
}

export function invalidateCurrentUserCache() {
  cachedUser = null;
  cachedUserPromise = null;
  cacheInitialized = false;
}
