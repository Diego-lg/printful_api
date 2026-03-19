/**
 * Printful Mockup Generator - Main JavaScript
 * Interactive preview system, form validation, and dynamic content
 */

// ================================================
// Global State
// ================================================

const appState = {
  currentStep: 1,
  selectedProduct: { productId: 257, variantId: 8852 },
  uploadedFile: null,
  designUrl: null,
  selectedPlacement: "front",
  currentBatchId: null,
  isGenerating: false,
};

// Preview State
const previewState = {
  layers: [],
  activeLayerId: null,
  isDragging: false,
  dragStartX: 0,
  dragStartY: 0,
  layerStartX: 0,
  layerStartY: 0,
  showGuides: true,
  lockAspectRatio: true,
  snapToCenter: false,
  canvasWidth: 0,
  canvasHeight: 0,
  productImage: null,
};

// Product configurations
const productConfigs = {
  257: {
    // T-Shirt
    front: {
      safeZone: { x: 25, y: 20, width: 50, height: 60 },
      defaultPosition: { x: 50, y: 40 },
    },
    back: {
      safeZone: { x: 25, y: 15, width: 50, height: 65 },
      defaultPosition: { x: 50, y: 40 },
    },
    left_chest: {
      safeZone: { x: 20, y: 25, width: 20, height: 20 },
      defaultPosition: { x: 30, y: 35 },
    },
    right_chest: {
      safeZone: { x: 60, y: 25, width: 20, height: 20 },
      defaultPosition: { x: 70, y: 35 },
    },
  },
  11: {
    // Mug
    front: {
      safeZone: { x: 15, y: 20, width: 70, height: 60 },
      defaultPosition: { x: 50, y: 50 },
    },
  },
  14: {
    // Tote
    front: {
      safeZone: { x: 20, y: 25, width: 60, height: 50 },
      defaultPosition: { x: 50, y: 50 },
    },
  },
  18: {
    // Poster
    front: {
      safeZone: { x: 10, y: 10, width: 80, height: 80 },
      defaultPosition: { x: 50, y: 50 },
    },
  },
};

// ================================================
// Initialization
// ================================================

document.addEventListener("DOMContentLoaded", function () {
  initializeApp();
});

function initializeApp() {
  setupEventListeners();
  updateProgressSteps();
  loadProductPreview();
}

// ================================================
// Event Listeners Setup
// ================================================

function setupEventListeners() {
  // Step navigation
  document
    .getElementById("step1-next")
    ?.addEventListener("click", () => goToStep(2));
  document
    .getElementById("step2-back")
    ?.addEventListener("click", () => goToStep(1));
  document
    .getElementById("step2-next")
    ?.addEventListener("click", () => goToStep(3));
  document
    .getElementById("step3-back")
    ?.addEventListener("click", () => goToStep(2));
  document
    .getElementById("step3-next")
    ?.addEventListener("click", generateMockup);
  document
    .getElementById("download-btn")
    ?.addEventListener("click", downloadMockup);
  document
    .getElementById("new-mockup-btn")
    ?.addEventListener("click", resetApp);

  // Product selection
  document.querySelectorAll(".product-card").forEach((card) => {
    card.addEventListener("click", () => selectProduct(card));
  });

  // File upload
  const uploadZone = document.getElementById("upload-zone");
  const fileInput = document.getElementById("file-input");

  if (uploadZone && fileInput) {
    uploadZone.addEventListener("click", () => fileInput.click());
    uploadZone.addEventListener("dragover", (e) => {
      e.preventDefault();
      uploadZone.classList.add("dragover");
    });
    uploadZone.addEventListener("dragleave", () => {
      uploadZone.classList.remove("dragover");
    });
    uploadZone.addEventListener("drop", (e) => {
      e.preventDefault();
      uploadZone.classList.remove("dragover");
      const files = e.dataTransfer.files;
      if (files.length > 0) handleFileSelect(files[0]);
    });
    fileInput.addEventListener("change", (e) => {
      if (e.target.files.length > 0) handleFileSelect(e.target.files[0]);
    });
  }

  // Remove file button
  document.getElementById("remove-file")?.addEventListener("click", removeFile);

  // Placement selection
  document.querySelectorAll(".placement-option").forEach((option) => {
    option.addEventListener("click", () =>
      selectPlacement(option.dataset.placement),
    );
  });

  // Preview controls
  setupPreviewControls();

  // Toggle switches
  document
    .getElementById("toggle-guides")
    ?.addEventListener("click", toggleGuides);
  document
    .getElementById("toggle-aspect")
    ?.addEventListener("click", toggleAspectRatio);
  document.getElementById("toggle-snap")?.addEventListener("click", toggleSnap);

  // Reset buttons
  document
    .getElementById("reset-position")
    ?.addEventListener("click", resetPosition);
  document.getElementById("reset-scale")?.addEventListener("click", resetScale);
  document
    .getElementById("reset-rotation")
    ?.addEventListener("click", resetRotation);
  document.getElementById("reset-all")?.addEventListener("click", resetAll);

  // Batch modal
  setupBatchModal();
}

// ================================================
// Step Navigation
// ================================================

function goToStep(step) {
  if (step === 2 && !appState.uploadedFile) {
    showToast("Please upload a design first", "error");
    return;
  }

  if (step === 3 && !appState.designUrl) {
    showToast("Please upload and process your design first", "error");
    return;
  }

  appState.currentStep = step;
  updateProgressSteps();
  showStep(step);

  if (step === 3) {
    loadProductPreview();
  }
}

function showStep(step) {
  document.querySelectorAll(".step-content").forEach((content) => {
    content.classList.remove("active");
  });
  document.getElementById(`step-${step}`)?.classList.add("active");
}

function updateProgressSteps() {
  document.querySelectorAll(".progress-step").forEach((step) => {
    const stepNum = parseInt(step.dataset.step);
    step.classList.remove("active", "completed");

    if (stepNum === appState.currentStep) {
      step.classList.add("active");
    } else if (stepNum < appState.currentStep) {
      step.classList.add("completed");
    }
  });
}

// ================================================
// Product Selection
// ================================================

function selectProduct(card) {
  document
    .querySelectorAll(".product-card")
    .forEach((c) => c.classList.remove("selected"));
  card.classList.add("selected");

  appState.selectedProduct = {
    productId: parseInt(card.dataset.productId),
    variantId: parseInt(card.dataset.variantId),
  };

  showToast("Product selected", "success");
}

// ================================================
// File Upload Handling
// ================================================

function handleFileSelect(file) {
  // Validate file type
  const allowedTypes = [
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/svg+xml",
  ];
  if (!allowedTypes.includes(file.type)) {
    showToast("Please upload a PNG, JPG, or SVG file", "error");
    return;
  }

  // Validate file size (10MB max)
  if (file.size > 10 * 1024 * 1024) {
    showToast("File size must be less than 10MB", "error");
    return;
  }

  appState.uploadedFile = file;

  // Show preview
  const reader = new FileReader();
  reader.onload = function (e) {
    const preview = document.getElementById("upload-preview");
    const previewImage = document.getElementById("preview-image");
    const previewName = document.getElementById("preview-name");
    const previewSize = document.getElementById("preview-size");
    const uploadZone = document.getElementById("upload-zone");

    if (preview && previewImage && previewName && previewSize && uploadZone) {
      previewImage.src = e.target.result;
      previewName.textContent = file.name;
      previewSize.textContent = formatFileSize(file.size);
      preview.classList.remove("hidden");
      uploadZone.classList.add("has-file");
    }

    // Enable continue button
    document.getElementById("step2-next")?.removeAttribute("disabled");

    // Also update preview state
    previewState.productImage = e.target.result;
  };
  reader.readAsDataURL(file);
}

function removeFile() {
  appState.uploadedFile = null;
  appState.designUrl = null;

  const preview = document.getElementById("upload-preview");
  const uploadZone = document.getElementById("upload-zone");
  const fileInput = document.getElementById("file-input");

  if (preview) preview.classList.add("hidden");
  if (uploadZone) uploadZone.classList.remove("has-file");
  if (fileInput) fileInput.value = "";
  document.getElementById("step2-next")?.setAttribute("disabled", "true");
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

// ================================================
// Placement Selection
// ================================================

function selectPlacement(placement) {
  appState.selectedPlacement = placement;

  document.querySelectorAll(".placement-option").forEach((option) => {
    option.classList.toggle("selected", option.dataset.placement === placement);
  });

  updateSafeZone();
  updateLayerPosition();
}

// ================================================
// Preview Controls
// ================================================

function setupPreviewControls() {
  // Scale slider
  const scaleSlider = document.getElementById("scale-slider");
  const scaleValue = document.getElementById("scale-value");

  if (scaleSlider && scaleValue) {
    scaleSlider.addEventListener("input", (e) => {
      const scale = parseInt(e.target.value);
      scaleValue.textContent = scale + "%";
      updateLayerScale(scale);
    });
  }

  // Rotation controls
  const rotationInput = document.getElementById("rotation-input");

  if (rotationInput) {
    rotationInput.addEventListener("input", (e) => {
      let rotation = parseInt(e.target.value) || 0;
      rotation = Math.max(0, Math.min(360, rotation));
      e.target.value = rotation;
      updateLayerRotation(rotation);
    });
  }

  document.getElementById("rotate-left")?.addEventListener("click", () => {
    const input = document.getElementById("rotation-input");
    if (input) {
      let value = parseInt(input.value) || 0;
      value = (value - 15 + 360) % 360;
      input.value = value;
      updateLayerRotation(value);
    }
  });

  document.getElementById("rotate-right")?.addEventListener("click", () => {
    const input = document.getElementById("rotation-input");
    if (input) {
      let value = parseInt(input.value) || 0;
      value = (value + 15) % 360;
      input.value = value;
      updateLayerRotation(value);
    }
  });

  // Add layer button
  document
    .getElementById("add-layer-btn")
    ?.addEventListener("click", addDesignLayer);

  // Setup canvas dragging
  setupCanvasDrag();
}

function loadProductPreview() {
  const productImage = document.getElementById("product-preview-image");
  if (!productImage) return;

  // Use hanger images for product previews (T-Shirt on hanger, others as placeholders)
  // Hanger SVG as data URL for T-Shirt product 257
  const hangerSvg =
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 500'%3E%3Crect fill='%23f1f5f9' width='400' height='500'/%3E%3Cpath fill='%23cbd5e1' d='M200 80 C180 80 165 95 165 115 L165 120 L120 120 L120 140 L155 140 L155 180 C130 190 110 220 110 260 C110 320 155 380 200 420 C245 380 290 320 290 260 C290 220 270 190 245 180 L245 140 L280 140 L280 120 L235 120 L235 115 C235 95 220 80 200 80 Z'/%3E%3Cpath fill='%2394a3b8' d='M195 75 L200 50 L205 75 L200 80 Z'/%3E%3Ccircle fill='%23647480' cx='200' cy='45' r='8'/%3E%3C/svg%3E";
  const productImages = {
    257: hangerSvg,
    11: "https://placehold.co/400x400/e2e8f0/94a3b8?text=Mug",
    14: "https://placehold.co/400x400/e2e8f0/94a3b8?text=Tote+Bag",
    18: "https://placehold.co/400x500/e2e8f0/94a3b8?text=Poster",
  };

  const imageUrl =
    productImages[appState.selectedProduct.productId] || productImages[257];
  productImage.src = imageUrl;

  productImage.onload = () => {
    const canvas = document.getElementById("preview-canvas");
    if (canvas) {
      previewState.canvasWidth = canvas.offsetWidth;
      previewState.canvasHeight = canvas.offsetHeight;
    }
    updateSafeZone();
    addDesignLayer();
  };
}

function updateSafeZone() {
  const safeZone = document.getElementById("safe-zone");
  if (!safeZone) return;

  const config =
    productConfigs[appState.selectedProduct.productId]?.[
      appState.selectedPlacement
    ];
  if (!config) {
    safeZone.classList.add("hidden");
    return;
  }

  const { safeZone: zone } = config;
  safeZone.style.left = zone.x + "%";
  safeZone.style.top = zone.y + "%";
  safeZone.style.width = zone.width + "%";
  safeZone.style.height = zone.height + "%";
  safeZone.classList.toggle("hidden", !previewState.showGuides);
}

function addDesignLayer() {
  if (!previewState.productImage) return;

  const overlay = document.getElementById("design-overlay");
  if (!overlay) return;

  const layerId = "layer-" + Date.now();
  const config =
    productConfigs[appState.selectedProduct.productId]?.[
      appState.selectedPlacement
    ];
  const defaultPos = config?.defaultPosition || { x: 50, y: 40 };

  const layer = {
    id: layerId,
    imageUrl: previewState.productImage,
    x: defaultPos.x,
    y: defaultPos.y,
    scale: 100,
    rotation: 0,
  };

  previewState.layers.push(layer);
  previewState.activeLayerId = layerId;

  renderLayers();
  renderLayerList();
}

function renderLayers() {
  const overlay = document.getElementById("design-overlay");
  if (!overlay) return;

  // Remove existing layer elements (except safe zone)
  overlay.querySelectorAll(".design-layer").forEach((el) => el.remove());

  previewState.layers.forEach((layer) => {
    const layerEl = document.createElement("div");
    layerEl.className = "design-layer";
    layerEl.dataset.layerId = layer.id;

    const img = document.createElement("img");
    img.src = layer.imageUrl;
    img.draggable = false;

    layerEl.appendChild(img);
    overlay.appendChild(layerEl);

    // Position and transform
    const transform = `translate(-50%, -50%) rotate(${layer.rotation}deg) scale(${layer.scale / 100})`;
    layerEl.style.left = layer.x + "%";
    layerEl.style.top = layer.y + "%";
    layerEl.style.transform = transform;

    // Click to select
    layerEl.addEventListener("click", (e) => {
      e.stopPropagation();
      selectLayer(layer.id);
    });
  });
}

function renderLayerList() {
  const layerList = document.getElementById("layer-list");
  if (!layerList) return;

  layerList.innerHTML = "";

  previewState.layers.forEach((layer) => {
    const item = document.createElement("div");
    item.className =
      "layer-item" + (layer.id === previewState.activeLayerId ? " active" : "");
    item.dataset.layerId = layer.id;

    const preview = document.createElement("img");
    preview.className = "layer-preview";
    preview.src = layer.imageUrl;

    const name = document.createElement("span");
    name.className = "layer-name";
    name.textContent = "Design Layer";

    item.appendChild(preview);
    item.appendChild(name);

    item.addEventListener("click", () => selectLayer(layer.id));

    layerList.appendChild(item);
  });
}

function selectLayer(layerId) {
  previewState.activeLayerId = layerId;
  const layer = previewState.layers.find((l) => l.id === layerId);

  if (layer) {
    // Update UI controls
    document.getElementById("scale-slider").value = layer.scale;
    document.getElementById("scale-value").textContent = layer.scale + "%";
    document.getElementById("rotation-input").value = layer.rotation;
  }

  renderLayerList();
  renderLayers();
}

function updateLayerScale(scale) {
  const layer = previewState.layers.find(
    (l) => l.id === previewState.activeLayerId,
  );
  if (layer) {
    layer.scale = scale;
    renderLayers();
  }
}

function updateLayerRotation(rotation) {
  const layer = previewState.layers.find(
    (l) => l.id === previewState.activeLayerId,
  );
  if (layer) {
    layer.rotation = rotation;
    renderLayers();
  }
}

function updateLayerPosition() {
  const config =
    productConfigs[appState.selectedProduct.productId]?.[
      appState.selectedPlacement
    ];
  const defaultPos = config?.defaultPosition || { x: 50, y: 40 };

  previewState.layers.forEach((layer) => {
    layer.x = defaultPos.x;
    layer.y = defaultPos.y;
  });

  renderLayers();
}

// ================================================
// Canvas Dragging
// ================================================

function setupCanvasDrag() {
  const canvas = document.getElementById("preview-canvas");
  if (!canvas) return;

  canvas.addEventListener("mousedown", startDrag);
  canvas.addEventListener("mousemove", drag);
  canvas.addEventListener("mouseup", endDrag);
  canvas.addEventListener("mouseleave", endDrag);

  // Touch events
  canvas.addEventListener("touchstart", startDragTouch);
  canvas.addEventListener("touchmove", dragTouch);
  canvas.addEventListener("touchend", endDrag);
}

function startDrag(e) {
  if (!previewState.activeLayerId) return;

  const layer = previewState.layers.find(
    (l) => l.id === previewState.activeLayerId,
  );
  if (!layer) return;

  previewState.isDragging = true;
  previewState.dragStartX = e.clientX;
  previewState.dragStartY = e.clientY;
  previewState.layerStartX = layer.x;
  previewState.layerStartY = layer.y;

  document.getElementById("preview-canvas")?.classList.add("dragging");
}

function drag(e) {
  if (!previewState.isDragging) return;

  const canvas = document.getElementById("preview-canvas");
  if (!canvas) return;

  const rect = canvas.getBoundingClientRect();
  const deltaX = ((e.clientX - previewState.dragStartX) / rect.width) * 100;
  const deltaY = ((e.clientY - previewState.dragStartY) / rect.height) * 100;

  const layer = previewState.layers.find(
    (l) => l.id === previewState.activeLayerId,
  );
  if (layer) {
    layer.x = Math.max(0, Math.min(100, previewState.layerStartX + deltaX));
    layer.y = Math.max(0, Math.min(100, previewState.layerStartY + deltaY));
    renderLayers();
  }
}

function endDrag() {
  previewState.isDragging = false;
  document.getElementById("preview-canvas")?.classList.remove("dragging");
}

function startDragTouch(e) {
  if (e.touches.length === 1) {
    const touch = e.touches[0];
    startDrag({ clientX: touch.clientX, clientY: touch.clientY });
  }
}

function dragTouch(e) {
  if (e.touches.length === 1) {
    e.preventDefault();
    const touch = e.touches[0];
    drag({ clientX: touch.clientX, clientY: touch.clientY });
  }
}

// ================================================
// Toggle Functions
// ================================================

function toggleGuides() {
  const toggle = document.getElementById("toggle-guides");
  if (toggle) {
    previewState.showGuides = !previewState.showGuides;
    toggle.classList.toggle("active", previewState.showGuides);
    updateSafeZone();
  }
}

function toggleAspectRatio() {
  const toggle = document.getElementById("toggle-aspect");
  if (toggle) {
    previewState.lockAspectRatio = !previewState.lockAspectRatio;
    toggle.classList.toggle("active", previewState.lockAspectRatio);
  }
}

function toggleSnap() {
  const toggle = document.getElementById("toggle-snap");
  if (toggle) {
    previewState.snapToCenter = !previewState.snapToCenter;
    toggle.classList.toggle("active", previewState.snapToCenter);
  }
}

// ================================================
// Reset Functions
// ================================================

function resetPosition() {
  const layer = previewState.layers.find(
    (l) => l.id === previewState.activeLayerId,
  );
  if (layer) {
    const config =
      productConfigs[appState.selectedProduct.productId]?.[
        appState.selectedPlacement
      ];
    const defaultPos = config?.defaultPosition || { x: 50, y: 40 };
    layer.x = defaultPos.x;
    layer.y = defaultPos.y;
    renderLayers();
  }
}

function resetScale() {
  const layer = previewState.layers.find(
    (l) => l.id === previewState.activeLayerId,
  );
  if (layer) {
    layer.scale = 100;
    document.getElementById("scale-slider").value = 100;
    document.getElementById("scale-value").textContent = "100%";
    renderLayers();
  }
}

function resetRotation() {
  const layer = previewState.layers.find(
    (l) => l.id === previewState.activeLayerId,
  );
  if (layer) {
    layer.rotation = 0;
    document.getElementById("rotation-input").value = 0;
    renderLayers();
  }
}

function resetAll() {
  resetPosition();
  resetScale();
  resetRotation();
}

// ================================================
// Mockup Generation
// ================================================

async function generateMockup() {
  if (appState.isGenerating) return;
  appState.isGenerating = true;

  goToStep(4);
  updateLoadingProgress(0, "Uploading your design...");

  try {
    // Upload file first
    updateLoadingProgress(20, "Uploading design to server...");
    const uploadResult = await uploadFile();

    if (!uploadResult.success) {
      throw new Error(uploadResult.error || "Failed to upload file");
    }

    appState.designUrl = uploadResult.data.r2_public_url;

    // Create mockup
    updateLoadingProgress(50, "Generating mockup...");
    const designParams = previewState.layers.map((layer, index) => ({
      name: `Layer ${index + 1}`,
      x: layer.x,
      y: layer.y,
      scale: layer.scale,
      rotation: layer.rotation,
    }));

    const mockupResult = await createMockupTask(
      appState.designUrl,
      designParams,
    );

    if (!mockupResult.success) {
      throw new Error(mockupResult.error || "Failed to create mockup");
    }

    // Poll for result
    updateLoadingProgress(70, "Processing mockup...");
    const taskKey =
      mockupResult.data.task_key || mockupResult.data.result?.task_key;

    if (taskKey) {
      await pollMockupResult(taskKey);
    } else {
      // Mockup might be synchronous
      updateLoadingProgress(100, "Mockup ready!");
      showMockupResult(null);
    }
  } catch (error) {
    showToast(error.message, "error");
    goToStep(3);
  } finally {
    appState.isGenerating = false;
  }
}

async function uploadFile() {
  const formData = new FormData();
  formData.append("file", appState.uploadedFile);
  formData.append("create_mockup", "false");

  const response = await fetch("/api/upload", {
    method: "POST",
    body: formData,
  });

  return response.json();
}

async function createMockupTask(imageUrl, designParams) {
  const response = await fetch("/api/mockups", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      image_url: imageUrl,
      design_params: designParams,
    }),
  });

  return response.json();
}

async function pollMockupResult(taskKey) {
  const maxAttempts = 30;
  const delay = 2000;

  for (let i = 0; i < maxAttempts; i++) {
    const response = await fetch(`/api/mockups/${taskKey}`);
    const result = await response.json();

    if (result.status === "completed") {
      updateLoadingProgress(100, "Mockup ready!");
      showMockupResult(result.mockups?.[0]?.url);
      return;
    } else if (result.status === "failed") {
      throw new Error("Mockup generation failed");
    }

    updateLoadingProgress(70 + (i / maxAttempts) * 30, "Processing mockup...");
    await new Promise((resolve) => setTimeout(resolve, delay));
  }

  throw new Error("Mockup generation timed out");
}

function updateLoadingProgress(percent, text) {
  const progressBar = document.getElementById("progress-bar");
  const loadingText = document.getElementById("loading-text");

  if (progressBar) progressBar.style.width = percent + "%";
  if (loadingText) loadingText.textContent = text;
}

function showMockupResult(mockupUrl) {
  const mockupImage = document.getElementById("final-mockup");
  if (mockupImage && mockupUrl) {
    mockupImage.src = mockupUrl;
  }
  goToStep(5);
}

function downloadMockup() {
  const mockupImage = document.getElementById("final-mockup");
  if (!mockupImage || !mockupImage.src) return;

  const link = document.createElement("a");
  link.href = mockupImage.src;
  link.download = "mockup-" + Date.now() + ".png";
  link.click();

  showToast("Mockup downloaded!", "success");
}

function resetApp() {
  appState.currentStep = 1;
  appState.uploadedFile = null;
  appState.designUrl = null;
  appState.isGenerating = false;

  previewState.layers = [];
  previewState.activeLayerId = null;

  removeFile();
  updateProgressSteps();
  showStep(1);

  // Reset controls
  document.getElementById("scale-slider").value = 100;
  document.getElementById("scale-value").textContent = "100%";
  document.getElementById("rotation-input").value = 0;
}

// ================================================
// Batch Modal
// ================================================

function setupBatchModal() {
  const modal = document.getElementById("batch-modal");
  const openBtn = document.getElementById("batch-test-btn");
  const closeBtn = document.getElementById("batch-close");

  openBtn?.addEventListener("click", () => modal?.classList.add("active"));
  closeBtn?.addEventListener("click", () => modal?.classList.remove("active"));

  modal?.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.remove("active");
  });

  // Batch file upload
  const batchUploadZone = document.getElementById("batch-upload-zone");
  const batchFileInput = document.getElementById("batch-file-input");

  batchUploadZone?.addEventListener("click", () => batchFileInput?.click());
  batchFileInput?.addEventListener("change", (e) => {
    if (e.target.files.length > 0) handleBatchFileSelect(e.target.files[0]);
  });

  // Batch config
  document
    .getElementById("batch-add-config-btn")
    ?.addEventListener("click", addBatchConfig);
  document
    .getElementById("batch-generate-btn")
    ?.addEventListener("click", generateBatchMockups);

  // Initialize with one config
  addBatchConfig();
}

let batchFile = null;

function handleBatchFileSelect(file) {
  const allowedTypes = ["image/png", "image/jpeg", "image/jpg"];
  if (!allowedTypes.includes(file.type)) {
    showToast("Please upload a PNG or JPG file", "error");
    return;
  }

  batchFile = file;

  const preview = document.getElementById("batch-preview");
  const previewImage = document.getElementById("batch-preview-image");
  const previewName = document.getElementById("batch-preview-name");
  const uploadZone = document.getElementById("batch-upload-zone");

  if (preview && previewImage && previewName && uploadZone) {
    const reader = new FileReader();
    reader.onload = (e) => {
      previewImage.src = e.target.result;
      previewName.textContent = file.name;
      preview.classList.remove("hidden");
      uploadZone.classList.add("has-file");
      document
        .getElementById("batch-generate-btn")
        ?.removeAttribute("disabled");
    };
    reader.readAsDataURL(file);
  }
}

const batchConfigs = [];

function addBatchConfig() {
  const configsList = document.getElementById("batch-configs-list");
  if (!configsList) return;

  const index = batchConfigs.length;
  const defaultConfigs = [
    { name: "Center, 100%", x: 50, y: 50, scale: 100, rotation: 0 },
    { name: "Top-Left, 80%", x: 30, y: 30, scale: 80, rotation: 0 },
    { name: "Bottom-Right, 120%", x: 70, y: 70, scale: 120, rotation: 45 },
  ];

  const config = defaultConfigs[index] || {
    name: `Config ${index + 1}`,
    x: 50,
    y: 50,
    scale: 100,
    rotation: 0,
  };
  batchConfigs.push(config);

  const item = document.createElement("div");
  item.className = "batch-config-item";
  item.dataset.index = index;

  item.innerHTML = `
    <div class="batch-config-header">
      <span class="batch-config-title">Configuration ${index + 1}</span>
      <button class="batch-config-remove" data-index="${index}">&times;</button>
    </div>
    <div class="batch-config-fields">
      <div class="batch-config-field">
        <label>X Position %</label>
        <input type="number" name="x" value="${config.x}" min="0" max="100">
      </div>
      <div class="batch-config-field">
        <label>Y Position %</label>
        <input type="number" name="y" value="${config.y}" min="0" max="100">
      </div>
      <div class="batch-config-field">
        <label>Scale %</label>
        <input type="number" name="scale" value="${config.scale}" min="10" max="200">
      </div>
      <div class="batch-config-field">
        <label>Rotation °</label>
        <input type="number" name="rotation" value="${config.rotation}" min="0" max="360">
      </div>
    </div>
  `;

  configsList.appendChild(item);

  // Remove button
  item.querySelector(".batch-config-remove")?.addEventListener("click", (e) => {
    const idx = parseInt(e.target.dataset.index);
    batchConfigs.splice(idx, 1);
    item.remove();
    updateConfigIndices();
  });
}

function updateConfigIndices() {
  document.querySelectorAll(".batch-config-item").forEach((item, idx) => {
    item.dataset.index = idx;
    item.querySelector(".batch-config-title").textContent =
      `Configuration ${idx + 1}`;
    item.querySelector(".batch-config-remove").dataset.index = idx;
  });
}

async function generateBatchMockups() {
  if (!batchFile) return;

  const configs = [];
  document.querySelectorAll(".batch-config-item").forEach((item) => {
    configs.push({
      x: parseInt(item.querySelector('input[name="x"]').value),
      y: parseInt(item.querySelector('input[name="y"]').value),
      scale: parseInt(item.querySelector('input[name="scale"]').value),
      rotation: parseInt(item.querySelector('input[name="rotation"]').value),
    });
  });

  // Upload file first
  const formData = new FormData();
  formData.append("file", batchFile);
  formData.append("create_mockup", "false");

  const uploadResponse = await fetch("/api/upload", {
    method: "POST",
    body: formData,
  });
  const uploadResult = await uploadResponse.json();

  if (!uploadResult.success) {
    showToast("Failed to upload file", "error");
    return;
  }

  // Show progress
  document.getElementById("batch-progress-section")?.classList.remove("hidden");
  const progressFill = document.getElementById("batch-progress-fill");
  const progressText = document.getElementById("batch-progress-text");

  // Create batch
  const batchResponse = await fetch("/api/batch-mockups", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      design_url: uploadResult.data.r2_public_url,
      configurations: configs,
    }),
  });

  const batchResult = await batchResponse.json();

  if (batchResult.success) {
    appState.currentBatchId = batchResult.batch_id;
    pollBatchResults(batchResult.batch_id);
  }
}

async function pollBatchResults(batchId) {
  const maxAttempts = 60;
  const delay = 3000;

  for (let i = 0; i < maxAttempts; i++) {
    const response = await fetch(`/api/batch-mockups/poll/${batchId}`);
    const result = await response.json();

    if (result.progress) {
      const percent = (result.progress.completed / result.progress.total) * 100;
      const progressFill = document.getElementById("batch-progress-fill");
      const progressText = document.getElementById("batch-progress-text");

      if (progressFill) progressFill.style.width = percent + "%";
      if (progressText)
        progressText.textContent = `Processing ${result.progress.completed}/${result.progress.total}...`;
    }

    if (
      result.batch?.status === "completed" ||
      result.batch?.status === "failed"
    ) {
      showBatchResults(result.batch);
      return;
    }

    await new Promise((resolve) => setTimeout(resolve, delay));
  }
}

function showBatchResults(batch) {
  document.getElementById("batch-progress-section")?.classList.add("hidden");
  document.getElementById("batch-results-section")?.classList.remove("hidden");

  const grid = document.getElementById("batch-results-grid");
  if (!grid) return;

  grid.innerHTML = "";

  batch.variations?.forEach((variation, idx) => {
    const item = document.createElement("div");
    item.className = "batch-result-item";

    const config = batch.configurations?.[idx] || {};

    item.innerHTML = `
      <img class="batch-result-image" src="${variation.local_url || variation.url}" alt="Mockup ${idx + 1}">
      <div class="batch-result-info">
        <div class="batch-result-config">
          Pos: (${config.x}%, ${config.y}%) | Scale: ${config.scale}% | Rot: ${config.rotation}°
        </div>
        <div class="batch-result-actions">
          <button class="batch-result-btn" onclick="downloadBatchMockup('${variation.url}')">Download</button>
        </div>
      </div>
    `;

    grid.appendChild(item);
  });
}

function downloadBatchMockup(url) {
  const link = document.createElement("a");
  link.href = url;
  link.download = "mockup-" + Date.now() + ".png";
  link.click();
}

// ================================================
// Toast Notifications
// ================================================

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${type === "success" ? "✓" : type === "error" ? "✕" : "ℹ"}</span>
    <span class="toast-message">${message}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// Export for global access
window.downloadBatchMockup = downloadBatchMockup;
