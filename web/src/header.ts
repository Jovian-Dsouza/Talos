// Site header for the landing, live, datasets and wallet pages: brand, nav, and the account slot
// (sign-in button, or the signed-in player's earnings chip linking to their wallet).
import { fetchWallet } from "./api";
import { authAvailable, devQuery, initAuth, onAuthChange, playerName, signIn } from "./auth";
import { escapeHtml } from "./format";
import { amount } from "./words";

export type Page = "home" | "live" | "datasets" | "wallet";

const LINKS: readonly [Page | "play", string, string][] = [
  ["play", "/play", "Play"],
  ["live", "/network", "Live"],
  ["datasets", "/datasets", "Datasets"],
  ["wallet", "/wallet", "Wallet"],
];
const WALLET_REFRESH_MS = 30_000;

export const link = (path: string): string => `${path}${devQuery}`;

async function renderAccount(slot: HTMLElement): Promise<void> {
  const name = playerName();
  if (name === null) {
    slot.innerHTML = authAvailable ? `<button type="button" class="btn small" id="header-sign-in">Sign in</button>` : "";
    slot.querySelector("#header-sign-in")?.addEventListener("click", signIn);
    return;
  }
  try {
    const wallet = await fetchWallet();
    slot.innerHTML = `<a class="chip-earned" href="${link("/wallet")}" title="Your wallet">
      <span class="mark" aria-hidden="true">τ</span>${amount(wallet.earned_tao)}<span class="sr">TAO earned</span></a>`;
  } catch {
    slot.innerHTML = `<a class="chip-earned" href="${link("/wallet")}">${escapeHtml(name)}</a>`;
  }
}

/** Fill `<header id="top">` and start auth. Resolves once sign-in state is known. */
export async function mountHeader(current: Page): Promise<void> {
  const header = document.getElementById("top");
  if (!header) return;
  const nav = LINKS.map(([page, path, label]) =>
    `<a href="${link(path)}"${page === current ? ' aria-current="page"' : ""}>${label}</a>`).join("");
  header.innerHTML = `<a class="brand" href="${link("/")}"><span class="mark" aria-hidden="true">τ</span>TauNet</a>
    <nav aria-label="Main">${nav}</nav><div class="account" id="account"></div>`;
  const slot = header.querySelector<HTMLElement>("#account")!;
  try {
    await initAuth();
  } catch (error) {
    console.warn("sign-in failed to load", error);
  }
  onAuthChange(() => void renderAccount(slot));
  await renderAccount(slot);
  window.setInterval(() => void renderAccount(slot), WALLET_REFRESH_MS);
}
