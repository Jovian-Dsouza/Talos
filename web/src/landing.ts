import { fetchNetwork } from "./api";

const set = (id: string, value: string) => {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
};

async function refresh(): Promise<void> {
  try {
    const net = await fetchNetwork();
    set("s-miners", String(net.miners.length));
    set("s-runs", String(net.miners.reduce((sum, m) => sum + m.accepted, 0)));
    set("s-validators", String(net.validators.length));
    set("s-block", net.block.toLocaleString());
  } catch (error) {
    console.debug("network stats unavailable", error);
  }
}

void refresh();
window.setInterval(() => void refresh(), 15000);
