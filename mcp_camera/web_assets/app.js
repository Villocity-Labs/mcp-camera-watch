const cameraSelect = document.querySelector("#camera-select");
const captureButton = document.querySelector("#capture-button");
const promptForm = document.querySelector("#prompt-form");
const askButton = document.querySelector("#ask-button");
const cameraImage = document.querySelector("#camera-image");
const cameraLoading = document.querySelector("#camera-loading");
const cameraEmpty = document.querySelector("#camera-empty");
const captureTime = document.querySelector("#capture-time");
const enhancePreview = document.querySelector("#enhance-preview");
const apiKeyInput = document.querySelector("#api-key");
const modelInput = document.querySelector("#model");
const detailSelect = document.querySelector("#detail");
const promptInput = document.querySelector("#prompt");
const responseTitle = document.querySelector("#response-title");
const responseOutput = document.querySelector("#response-output");
const modelUsed = document.querySelector("#model-used");
const requestStatus = document.querySelector("#request-status");

async function api(path, body) {
  const options = body
    ? {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }
    : {};
  const response = await fetch(path, options);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `Request failed with HTTP ${response.status}`);
  }
  return payload;
}

function setBusy(busy, status) {
  captureButton.disabled = busy;
  askButton.disabled = busy;
  cameraLoading.hidden = !busy;
  requestStatus.classList.remove("error");
  requestStatus.textContent = status;
}

function showError(error) {
  requestStatus.classList.add("error");
  requestStatus.textContent = error.message;
}

function showFrame(payload) {
  cameraImage.src = payload.frame_data_url;
  cameraImage.classList.toggle("enhanced", enhancePreview.checked);
  cameraImage.hidden = false;
  cameraEmpty.hidden = true;
  captureTime.textContent = new Date(payload.captured_at || payload.observed_at).toLocaleString();
  captureTime.hidden = false;
}

enhancePreview.addEventListener("change", () => {
  cameraImage.classList.toggle("enhanced", enhancePreview.checked);
});

async function loadCameras() {
  try {
    const payload = await api("/api/cameras");
    modelInput.value = payload.model;
    cameraSelect.replaceChildren(
      ...payload.cameras.map((camera) => {
        const option = document.createElement("option");
        option.value = camera.id;
        option.textContent = `${camera.name} · ${camera.type}`;
        return option;
      }),
    );
    if (!payload.cameras.length) {
      captureButton.disabled = true;
      askButton.disabled = true;
      requestStatus.textContent = "No cameras are configured.";
    }
  } catch (error) {
    showError(error);
  }
}

captureButton.addEventListener("click", async () => {
  setBusy(true, "Capturing current frame...");
  try {
    const payload = await api("/api/snapshot", { camera_id: cameraSelect.value });
    showFrame(payload);
    setBusy(false, "Frame captured");
  } catch (error) {
    setBusy(false, "Capture failed");
    showError(error);
  }
});

promptForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setBusy(true, "Capturing and asking OpenAI...");
  responseTitle.textContent = "Request in progress";
  responseOutput.textContent = "";
  modelUsed.textContent = "";
  const apiKey = apiKeyInput.value;
  apiKeyInput.value = "";
  try {
    const payload = await api("/api/describe", {
      camera_id: cameraSelect.value,
      api_key: apiKey,
      model: modelInput.value,
      detail: detailSelect.value,
      prompt: promptInput.value,
    });
    showFrame(payload);
    responseTitle.textContent = "Latest observation";
    responseOutput.textContent = payload.description;
    modelUsed.textContent = payload.model || payload.provider;
    setBusy(false, "Response received");
  } catch (error) {
    responseTitle.textContent = "Request failed";
    responseOutput.textContent = error.message;
    setBusy(false, "Request failed");
    showError(error);
  }
});

loadCameras();
