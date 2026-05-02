/* ═══════════════════════════════════════
   PINFLOW · script.js
═══════════════════════════════════════ */

let state = {
  title: "",
  link: "",
  selectedImage: null,
  images: [],
};

/* ─────────────────────────────────────
   FETCH PRODUCT + IMAGES
───────────────────────────────────── */
async function fetchProduct() {
  const link = document.getElementById("linkInput").value.trim();
  if (!link) return shakInput();

  setLoading(true, "Fetching product data…");
  hide("productStrip");
  hide("gridSection");
  hide("resultSection");

  try {
    const res = await fetch("/api/fetch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ link }),
    });

    if (!res.ok) throw new Error("Server error");
    const data = await res.json();

    state.title = data.title;
    state.link = data.link;
    state.images = data.images;
    state.selectedImage = null;

    // Product strip
    document.getElementById("stripTitle").textContent = data.title;
    const stripLink = document.getElementById("stripLink");
    stripLink.href = data.link;

    const stripImgWrap = document.getElementById("stripImgWrap");
    if (data.product_image) {
      document.getElementById("stripImg").src = data.product_image;
      show("stripImgWrap");
    } else {
      hide("stripImgWrap");
    }

    show("productStrip");

    // Render grid
    setLoading(true, "Loading images…");
    renderGrid(data.images);

    setTimeout(() => {
      setLoading(false);
      show("gridSection");
      scrollTo("gridSection");
    }, 300);

  } catch (err) {
    setLoading(false);
    alert("Could not fetch product. Check the link and try again.");
  }
}


/* ─────────────────────────────────────
   RENDER MASONRY GRID
───────────────────────────────────── */
function renderGrid(images) {
  const grid = document.getElementById("masonryGrid");
  grid.innerHTML = "";

  images.forEach((src, i) => {
    const item = document.createElement("div");
    item.className = "grid-item";
    item.dataset.index = i;
    item.onclick = () => selectImage(item, src);

    const img = document.createElement("img");
    img.src = src;
    img.alt = "Product image option";
    img.loading = "lazy";

    const overlay = document.createElement("div");
    overlay.className = "grid-item-overlay";

    const chip = document.createElement("button");
    chip.className = "select-chip";
    chip.textContent = "Select";
    chip.onclick = (e) => { e.stopPropagation(); selectImage(item, src); };
    overlay.appendChild(chip);

    const badge = document.createElement("div");
    badge.className = "selected-badge";
    badge.textContent = "✓ Selected";

    item.appendChild(img);
    item.appendChild(overlay);
    item.appendChild(badge);
    grid.appendChild(item);
  });

  hide("generateBar");
}


/* ─────────────────────────────────────
   SELECT IMAGE
───────────────────────────────────── */
function selectImage(item, src) {
  document.querySelectorAll(".grid-item").forEach(el => el.classList.remove("selected"));
  item.classList.add("selected");
  state.selectedImage = src;

  // Update generate bar
  const bar = document.getElementById("generateBar");
  document.getElementById("genThumb").src = src;
  document.getElementById("genLabel").textContent = "1 image selected";
  show("generateBar");
}


/* ─────────────────────────────────────
   GENERATE PIN CONTENT
───────────────────────────────────── */
async function generatePin() {
  if (!state.selectedImage) return;

  setLoading(true, "Generating your Pinterest card…");
  hide("gridSection");
  hide("resultSection");

  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: state.title,
        selected_image: state.selectedImage,
        link: state.link,
      }),
    });

    if (!res.ok) throw new Error("Server error");
    const data = await res.json();

    // Populate result
    document.getElementById("pinImage").src = data.image;
    document.getElementById("pinCardTitle").textContent = data.title;
    document.getElementById("pinCardTags").textContent = data.hashtags;

    document.getElementById("titleField").value = data.title;
    document.getElementById("descField").value = data.description;
    document.getElementById("tagsField").value = data.hashtags;

    const pl = document.getElementById("productLink");
    pl.href = data.link || state.link;

    setLoading(false);
    show("gridSection");
    show("resultSection");
    scrollTo("resultSection");

  } catch (err) {
    setLoading(false);
    show("gridSection");
    alert("Generation failed. Please try again.");
  }
}


/* ─────────────────────────────────────
   COPY FIELD
───────────────────────────────────── */
function copyField(fieldId, btn) {
  const el = document.getElementById(fieldId);
  const text = el.value;

  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.textContent;
    btn.textContent = "✓ Copied!";
    btn.classList.add("copied");
    setTimeout(() => {
      btn.textContent = orig;
      btn.classList.remove("copied");
    }, 2000);
  }).catch(() => {
    el.select();
    document.execCommand("copy");
  });
}


/* ─────────────────────────────────────
   RESET
───────────────────────────────────── */
function resetAll() {
  state = { title: "", link: "", selectedImage: null, images: [] };
  document.getElementById("linkInput").value = "";
  hide("productStrip");
  hide("gridSection");
  hide("resultSection");
  hide("loaderWrap");
  window.scrollTo({ top: 0, behavior: "smooth" });
}


/* ─────────────────────────────────────
   HELPERS
───────────────────────────────────── */
function show(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = "";
}

function hide(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = "none";
}

function setLoading(on, msg) {
  const wrap = document.getElementById("loaderWrap");
  const txt  = document.getElementById("loaderText");
  const btn  = document.getElementById("fetchBtn");

  if (on) {
    if (txt && msg) txt.textContent = msg;
    wrap.style.display = "flex";
    if (btn) btn.disabled = true;
  } else {
    wrap.style.display = "none";
    if (btn) btn.disabled = false;
  }
}

function scrollTo(id) {
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
}

function shakInput() {
  const box = document.getElementById("searchBox");
  box.style.animation = "none";
  box.offsetHeight; // reflow
  box.style.animation = "shake 0.4s ease";
  setTimeout(() => { box.style.animation = ""; }, 400);
}

/* shake animation injected */
const style = document.createElement("style");
style.textContent = `
@keyframes shake {
  0%,100% { transform: translateX(0); }
  20%      { transform: translateX(-8px); }
  40%      { transform: translateX(8px); }
  60%      { transform: translateX(-5px); }
  80%      { transform: translateX(5px); }
}`;
document.head.appendChild(style);

/* Enter key triggers fetch */
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("linkInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter") fetchProduct();
  });
});