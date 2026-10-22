const state = { metadata: null, page: null, start: null, region: null };
const svg = document.querySelector("#overlay");
const selection = document.querySelector("#selection");
const image = document.querySelector("#page-image");

function point(event) {
  const rect = svg.getBoundingClientRect();
  const page = state.page;
  return {
    x: Math.max(0, Math.min(page.width, ((event.clientX - rect.left) / rect.width) * page.width)),
    y: Math.max(0, Math.min(page.height, ((event.clientY - rect.top) / rect.height) * page.height)),
  };
}

function renderRegion(region) {
  if (!region) {
    selection.setAttribute("visibility", "hidden");
    return;
  }
  const x = Math.min(region.x0, region.x1);
  const y = Math.min(region.top, region.bottom);
  selection.setAttribute("x", x);
  selection.setAttribute("y", y);
  selection.setAttribute("width", Math.abs(region.x1 - region.x0));
  selection.setAttribute("height", Math.abs(region.bottom - region.top));
  selection.setAttribute("visibility", "visible");
}

function renderCoordinates() {
  const output = document.querySelector("#coordinates");
  if (!state.region) {
    output.innerHTML = "<dt>Selection</dt><dd>Draw a rectangle on the page.</dd>";
    return;
  }
  const region = state.region;
  output.innerHTML = `<dt>Page</dt><dd>${state.page.page_number}</dd>
    <dt>x0 / top</dt><dd>${region.x0.toFixed(1)} / ${region.top.toFixed(1)}</dd>
    <dt>x1 / bottom</dt><dd>${region.x1.toFixed(1)} / ${region.bottom.toFixed(1)}</dd>`;
}

function selectPage(page) {
  state.page = page;
  state.region = null;
  svg.setAttribute("viewBox", `0 0 ${page.width} ${page.height}`);
  image.src = `/api/pages/${page.page_number}.png`;
  document.querySelectorAll(".page-tabs button").forEach((button) => {
    button.classList.toggle("active", Number(button.dataset.page) === page.page_number);
  });
  renderRegion(null);
  renderCoordinates();
}

async function initialise() {
  const response = await fetch("/api/session");
  const metadata = await response.json();
  state.metadata = metadata;
  document.querySelector("#context").textContent = `${metadata.company_id} · ${metadata.reporting_basis} · ${metadata.period_label} · ${metadata.target_scope_id}`;
  const tabs = document.querySelector("#page-tabs");
  metadata.pages.forEach((page) => {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.page = page.page_number;
    button.textContent = `Page ${page.page_number} (${page.selection_role})`;
    button.addEventListener("click", () => selectPage(page));
    tabs.appendChild(button);
  });
  const primary = metadata.pages.find((page) => page.selection_role === "primary");
  selectPage(primary || metadata.pages[0]);
}

svg.addEventListener("pointerdown", (event) => {
  state.start = point(event);
  svg.setPointerCapture(event.pointerId);
  state.region = { x0: state.start.x, top: state.start.y, x1: state.start.x, bottom: state.start.y };
  renderRegion(state.region);
  renderCoordinates();
});
svg.addEventListener("pointermove", (event) => {
  if (!state.start) return;
  const current = point(event);
  state.region = { x0: state.start.x, top: state.start.y, x1: current.x, bottom: current.y };
  renderRegion(state.region);
  renderCoordinates();
});
svg.addEventListener("pointerup", (event) => {
  if (!state.start) return;
  const current = point(event);
  state.region = {
    x0: Math.min(state.start.x, current.x), top: Math.min(state.start.y, current.y),
    x1: Math.max(state.start.x, current.x), bottom: Math.max(state.start.y, current.y),
  };
  state.start = null;
  renderRegion(state.region);
  renderCoordinates();
});

document.querySelector("#draft-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.region) {
    alert("Draw a rectangle first.");
    return;
  }
  const payload = {
    draft_id: document.querySelector("#draft-id").value,
    profile_version: document.querySelector("#profile-version").value,
    reviewer_name: document.querySelector("#reviewer-name").value,
    review_notes: document.querySelector("#review-notes").value,
    page_number: state.page.page_number,
    ...state.region,
  };
  const response = await fetch("/api/region-drafts", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  });
  const result = await response.json();
  if (!response.ok) {
    alert(result.detail || "Unable to save the region draft.");
    return;
  }
  document.querySelector("#result").hidden = false;
  document.querySelector("#saved-message").textContent = `Saved draft ${result.draft.draft_id}. Review the extracted text below before any later approval step.`;
  document.querySelector("#preview-text").textContent = result.preview_text;
});

initialise().catch((error) => { document.querySelector("#context").textContent = `Unable to load review session: ${error}`; });
