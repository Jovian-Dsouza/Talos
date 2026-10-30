import { Clerk } from "@clerk/clerk-js";
import { CLERK_KEY, DEV_LOGIN } from "./config";

let clerk: Clerk | null = null;
const devName = DEV_LOGIN ? new URLSearchParams(window.location.search).get("dev") : null;
const listeners = new Set<() => void>();

export const authAvailable = Boolean(devName || CLERK_KEY);

export async function initAuth(): Promise<void> {
  if (devName || !CLERK_KEY) return;
  clerk = new Clerk(CLERK_KEY);
  await clerk.load();
  clerk.addListener(() => listeners.forEach((notify) => notify()));
}

export function onAuthChange(notify: () => void): void {
  listeners.add(notify);
}

/** The signed-in player's display name, or null when signed out. */
export function playerName(): string | null {
  if (devName) return devName;
  const user = clerk?.user;
  if (!user) return null;
  return user.firstName || user.username || user.primaryEmailAddress?.emailAddress.split("@")[0] || "player";
}

export async function authHeaders(): Promise<Record<string, string>> {
  if (devName) return { Authorization: `Bearer dev:${devName}` };
  const token = await clerk?.session?.getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function signIn(): void {
  clerk?.openSignIn({ forceRedirectUrl: window.location.href, signUpForceRedirectUrl: window.location.href });
}

export async function signOut(): Promise<void> {
  await clerk?.signOut();
}
