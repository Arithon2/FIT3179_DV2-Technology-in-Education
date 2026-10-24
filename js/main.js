// Each .vega-host names its spec in data-spec; vegaEmbed renders it.
const OPTS = {
  renderer: "svg",
  actions: { export: true, source: false, compiled: false, editor: false },
  tooltip: { theme: "light" },
};

function makeResponsive(host) {
  const svg = host.querySelector("svg");
  if (!svg) return;
  const w = parseFloat(svg.getAttribute("width"));
  const h = parseFloat(svg.getAttribute("height"));
  if (!w || !h) return;
  svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
  svg.removeAttribute("width");
  svg.removeAttribute("height");
  svg.style.width = "100%";
  svg.style.maxWidth = `${w}px`;
}

async function render(host) {
  const url = host.dataset.spec;
  try {
    const res = await vegaEmbed(host, url, OPTS);
    makeResponsive(host);
    host.setAttribute("aria-busy", "false");
    return res;
  } catch (err) {
    host.innerHTML = `<p class="small">This chart could not load (${url}). Serve the folder over HTTP, e.g. <code>python -m http.server</code>.</p>`;
    console.error(url, err);
  }
}

document.fonts.ready.then(() => {
  document.querySelectorAll(".vega-host").forEach(render);
});
