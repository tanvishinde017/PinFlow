/* ─────────────────────────────────────────────
   PinFlow Pro — script.js
   Amazon → AI Pinterest Content Generator
───────────────────────────────────────────── */

// ── STATE ──────────────────────────────────────
const state = {
  link:          "",
  title:         "",
  price:         "N/A",
  productImage:  null,
  selectedImage: null,
  tone:          "viral",
  content:       null,
};

// ── DOM REFS ────────────────────────────────────
const $ = (id) => document.getElementById(id);

const urlInput      = $("product-url");
const fetchBtn      = $("fetch-btn");
const generateBtn   = $("generate-btn");
const variationsBtn = $("variations-btn");
const saveBtn       = $("save-btn");
const copyBtn       = $("copy-btn");
const resetBtn      = $("reset-btn");

const stepProduct    = $("step-product");
const stepImages     = $("step-images");
const stepContent    = $("step-content");
const stepVariations = $("step-variations");

const imageGrid      = $("image-grid");
const variationsGrid = $("variations-grid");
const historyList    = $("history-list");
const historyCount   = $("history-count");
const saveSuccess    = $("save-success");

// ── TABS ────────────────────────────────────────
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-section").forEach((s) => s.classList.remove("active"));

    btn.classList.add("active");
    const section = document.getElementById(`tab-${btn.dataset.tab}`);
    section.classList.add("active");

    if (btn.dataset.tab === "history") loadHistory();
  });
});

// ── TONE PILLS ──────────────────────────────────
document.querySelectorAll(".tone-pill").forEach((pill) => {
  pill.addEventListener("click", () => {
    document.querySelectorAll(".tone-pill").forEach((p) => p.classList.remove("active"));
    pill.classList.add("active");
    state.tone = pill.dataset.tone;
  });
});

// ── LOADING HELPERS ─────────────────────────────
function setLoading(btn, loading) {
  const text   = btn.querySelector(".btn-text");
  const loader = btn.querySelector(".btn-loader");
  btn.disabled = loading;
  if (loading) {
    text?.classList.add("hidden");
    loader?.classList.remove("hidden");
  } else {
    text?.classList.remove("hidden");
    loader?.classList.add("hidden");
  }
}

// ── CHAR COUNTERS ───────────────────────────────
$("out-title").addEventListener("input", function () {
  $("title-count").textContent = `${this.value.length}/100`;
});
$("out-desc").addEventListener("input", function () {
  $("desc-count").textContent = `${this.value.length}/500`;
});

// ── STEP 1: FETCH PRODUCT ───────────────────────
fetchBtn.addEventListener("click", fetchProduct);
urlInput.addEventListener("keydown", (e) => { if (e.key === "Enter") fetchProduct(); });

async function fetchProduct() {
  const link = urlInput.value.trim();
  if (!link) return flash(urlInput, "Please paste an Amazon URL first.");

  setLoading(fetchBtn, true);

  try {
    const res  = await fetch("/api/fetch", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ link }),
    });
    const data = await res.json();

    if (data.error) throw new Error(data.error);

    // Populate state
    state.link  = link;
    state.title = data.title;
    state.price = data.price;
    state.productImage = data.product_image;

    // Show product card
    $("product-title-display").textContent = data.title;
    $("product-price-display").textContent = data.price !== "N/A" ? data.price : "Price unavailable";

    const productImg = $("product-img");
    if (data.product_image) {
      productImg.src = data.product_image;
    } else {
      productImg.src = `https://picsum.photos/seed/${Math.floor(Math.random()*999)}/300/400`;
    }

    reveal(stepProduct);

    // Render image picker
    renderImageGrid(data.images);
    reveal(stepImages);

    // Scroll to product
    stepProduct.scrollIntoView({ behavior: "smooth", block: "start" });

  } catch (err) {
    showError("Could not fetch product. Try a direct Amazon product URL.");
    console.error(err);
  }

  setLoading(fetchBtn, false);
}

// ── IMAGE GRID ──────────────────────────────────
function renderImageGrid(images) {
  imageGrid.innerHTML = "";
  images.forEach((src) => {
    const div = document.createElement("div");
    div.className = "img-option";
    div.innerHTML = `
      <img src="${src}" alt="Option" loading="lazy" />
      <div class="check-mark">✓</div>
    `;
    div.addEventListener("click", () => selectImage(div, src));
    imageGrid.appendChild(div);
  });

  // Auto-select first
  if (imageGrid.firstChild) {
    selectImage(imageGrid.firstChild, images[0]);
  }
}

function selectImage(el, src) {
  document.querySelectorAll(".img-option").forEach((i) => i.classList.remove("selected"));
  el.classList.add("selected");
  state.selectedImage = src;
}

// ── STEP 2: GENERATE AI CONTENT ─────────────────
generateBtn.addEventListener("click", generateContent);

async function generateContent() {
  if (!state.title) return;

  setLoading(generateBtn, true);
  stepContent.classList.add("hidden");

  try {
    const res  = await fetch("/api/generate", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ title: state.title, price: state.price, tone: state.tone }),
    });
    const data = await res.json();

    state.content = data;

    // Populate editor
    $("out-title").value = data.pin_title || "";
    $("out-desc").value  = data.description || "";
    $("out-tags").value  = data.hashtags || "";
    $("out-cta").value   = data.cta || "";

    // Update char counts
    $("title-count").textContent = `${($("out-title").value).length}/100`;
    $("desc-count").textContent  = `${($("out-desc").value).length}/500`;

    reveal(stepContent);
    stepContent.scrollIntoView({ behavior: "smooth", block: "start" });

    // Reset save banner
    saveSuccess.classList.add("hidden");

  } catch (err) {
    showError("AI generation failed. Please try again.");
    console.error(err);
  }

  setLoading(generateBtn, false);
}

// ── A/B VARIATIONS ──────────────────────────────
variationsBtn.addEventListener("click", async () => {
  if (!state.title) return;

  variationsBtn.textContent = "Generating…";
  variationsBtn.disabled = true;
  stepVariations.classList.add("hidden");

  try {
    const res  = await fetch("/api/variations", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ title: state.title, price: state.price }),
    });
    const data = await res.json();

    renderVariations(data.variations || []);
    reveal(stepVariations);
    stepVariations.scrollIntoView({ behavior: "smooth", block: "start" });

  } catch (err) {
    showError("Could not generate variations.");
    console.error(err);
  }

  variationsBtn.textContent = "A/B All Tones";
  variationsBtn.disabled = false;
});

function renderVariations(variations) {
  variationsGrid.innerHTML = "";
  variations.forEach((v) => {
    const card = document.createElement("div");
    card.className = "variation-card";
    card.innerHTML = `
      <p class="variation-tone tone-${v.tone}">${toneEmoji(v.tone)} ${capitalize(v.tone)}</p>
      <p class="variation-title">${v.pin_title || ""}</p>
      <p class="variation-desc">${v.description || ""}</p>
      <p class="variation-tags">${v.hashtags || ""}</p>
      <button class="variation-select">Use this →</button>
    `;
    card.querySelector(".variation-select").addEventListener("click", () => {
      state.content = v;
      state.tone = v.tone;
      $("out-title").value = v.pin_title || "";
      $("out-desc").value  = v.description || "";
      $("out-tags").value  = v.hashtags || "";
      $("out-cta").value   = v.cta || "";
      reveal(stepContent);
      stepContent.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    variationsGrid.appendChild(card);
  });
}

function toneEmoji(tone) {
  return { viral: "🔥", luxury: "💎", casual: "😊", affiliate: "💰" }[tone] || "";
}
function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

// ── SAVE PIN ─────────────────────────────────────
saveBtn.addEventListener("click", async () => {
  if (!state.content) return;

  setLoading(saveBtn, true);

  const payload = {
    pin_title:      $("out-title").value,
    description:    $("out-desc").value,
    hashtags:       $("out-tags").value,
    cta:            $("out-cta").value,
    tone:           state.tone,
    selected_image: state.selectedImage,
    link:           state.link,
  };

  try {
    await fetch("/api/save", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(payload),
    });
    saveSuccess.classList.remove("hidden");
    setTimeout(() => saveSuccess.classList.add("hidden"), 3000);
  } catch (err) {
    showError("Save failed. Please try again.");
  }

  setLoading(saveBtn, false);
});

// ── COPY CONTENT ─────────────────────────────────
copyBtn.addEventListener("click", () => {
  const text = [
    $("out-title").value,
    "",
    $("out-desc").value,
    "",
    $("out-tags").value,
    "",
    $("out-cta").value,
  ].join("\n");

  navigator.clipboard.writeText(text).then(() => {
    copyBtn.textContent = "Copied! ✓";
    setTimeout(() => (copyBtn.textContent = "Copy Content"), 2000);
  });
});

// ── RESET ─────────────────────────────────────────
resetBtn.addEventListener("click", () => {
  urlInput.value = "";
  Object.assign(state, { link: "", title: "", price: "N/A", selectedImage: null, content: null });
  [stepProduct, stepImages, stepContent, stepVariations].forEach((el) =>
    el.classList.add("hidden")
  );
  window.scrollTo({ top: 0, behavior: "smooth" });
});

// ── HISTORY ───────────────────────────────────────
async function loadHistory() {
  try {
    const res  = await fetch("/api/history");
    const data = await res.json();

    historyCount.textContent = data.length;

    if (!data.length) {
      historyList.innerHTML = `<p class="empty-state">No pins saved yet. Create your first one!</p>`;
      return;
    }

    historyList.innerHTML = "";
    // Show newest first
    [...data].reverse().forEach((pin, idx) => {
      const item = document.createElement("div");
      item.className = "history-item";
      item.innerHTML = `
        <img
          class="history-thumb"
          src="${pin.image || `https://picsum.photos/seed/${idx}/150/200`}"
          alt="Pin"
          loading="lazy"
        />
        <div class="history-meta">
          <p class="history-pin-title">${pin.pin_title || "Untitled Pin"}</p>
          <p class="history-desc">${pin.description || ""}</p>
          <p class="history-date">${formatDate(pin.created_at)}</p>
        </div>
        <div class="history-actions">
          <button class="btn-icon" title="Preview">👁</button>
          <button class="btn-icon danger" title="Delete">✕</button>
        </div>
      `;

      // Preview
      item.querySelector(".btn-icon:not(.danger)").addEventListener("click", (e) => {
        e.stopPropagation();
        openModal(pin);
      });

      // Click row → preview
      item.addEventListener("click", () => openModal(pin));

      // Delete
      item.querySelector(".btn-icon.danger").addEventListener("click", async (e) => {
        e.stopPropagation();
        const realIdx = data.length - 1 - idx; // correct index for reversed display
        await fetch(`/api/history/${realIdx}`, { method: "DELETE" });
        item.style.opacity = "0";
        setTimeout(() => loadHistory(), 300);
      });

      historyList.appendChild(item);
    });

  } catch (err) {
    console.error("History load failed:", err);
  }
}

// ── MODAL ─────────────────────────────────────────
const modal = $("pin-modal");

function openModal(pin) {
  $("modal-img").src     = pin.image || `https://picsum.photos/seed/42/400/600`;
  $("modal-title").textContent = pin.pin_title || "Untitled";
  $("modal-desc").textContent  = pin.description || "";
  $("modal-tags").textContent  = pin.hashtags || "";
  $("modal-cta").textContent   = pin.cta || "Shop now";
  $("modal-tone").textContent  = `${toneEmoji(pin.tone)} ${capitalize(pin.tone || "viral")} tone`;
  modal.classList.remove("hidden");
}

$("modal-close").addEventListener("click", () => modal.classList.add("hidden"));
modal.addEventListener("click", (e) => { if (e.target === modal) modal.classList.add("hidden"); });

$("modal-copy-btn").addEventListener("click", () => {
  const text = [
    $("modal-title").textContent,
    "",
    $("modal-desc").textContent,
    "",
    $("modal-tags").textContent,
  ].join("\n");
  navigator.clipboard.writeText(text).then(() => {
    $("modal-copy-btn").textContent = "Copied! ✓";
    setTimeout(() => ($("modal-copy-btn").textContent = "Copy All"), 2000);
  });
});

// ── UTILS ──────────────────────────────────────────
function reveal(el) {
  el.classList.remove("hidden");
}

function formatDate(dateStr) {
  if (!dateStr) return "";
  try {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short", day: "numeric", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch { return dateStr; }
}

function flash(el, msg) {
  el.style.borderColor = "var(--accent)";
  el.placeholder = msg;
  setTimeout(() => {
    el.style.borderColor = "";
    el.placeholder = "https://www.amazon.com/dp/...";
  }, 2000);
}

function showError(msg) {
  const div = document.createElement("div");
  div.style.cssText = `
    position: fixed; bottom: 24px; right: 24px; z-index: 999;
    background: #3b0a14; border: 1px solid #e63462; border-radius: 10px;
    color: #f87171; padding: 14px 20px; font-size: 14px; font-weight: 600;
    animation: slideUp 0.3s ease;
  `;
  div.textContent = "⚠ " + msg;
  document.body.appendChild(div);
  setTimeout(() => div.remove(), 4000);
}