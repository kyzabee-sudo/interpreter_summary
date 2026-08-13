const form = document.getElementById("summarize-form");
const pdfInput = document.getElementById("pdf-input");
const styleInput = document.getElementById("style-input");
const notesInput = document.getElementById("notes-input");
const dropzone = document.getElementById("dropzone");
const pdfName = document.getElementById("pdf-name");
const statusEl = document.getElementById("status");
const submitBtn = document.getElementById("submit-btn");
const resultEl = document.getElementById("result");
const resultHtml = document.getElementById("result-html");
const resultMeta = document.getElementById("result-meta");
const copyBtn = document.getElementById("copy-btn");
const mdBtn = document.getElementById("md-btn");
const docxBtn = document.getElementById("docx-btn");

let lastMarkdown = "";

function setStatus(message, show = true) {
  statusEl.hidden = !show;
  statusEl.textContent = message;
}

pdfInput.addEventListener("change", () => {
  pdfName.textContent = pdfInput.files[0] ? pdfInput.files[0].name : "";
});

["dragenter", "dragover"].forEach((eventName) => {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.add("dragover");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.remove("dragover");
  });
});

dropzone.addEventListener("drop", (event) => {
  const file = event.dataTransfer.files[0];
  if (!file) return;
  const transfer = new DataTransfer();
  transfer.items.add(file);
  pdfInput.files = transfer.files;
  pdfName.textContent = file.name;
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!pdfInput.files[0]) {
    setStatus("Choose a PDF first.");
    return;
  }

  const body = new FormData();
  body.append("pdf", pdfInput.files[0]);
  if (styleInput.files[0]) body.append("style", styleInput.files[0]);
  if (notesInput.value.trim()) body.append("notes", notesInput.value.trim());

  submitBtn.disabled = true;
  resultEl.hidden = true;
  setStatus("Uploading the PDF and asking Grok to read the article. Longer papers can take a few minutes.");

  try {
    const response = await fetch("/api/summarize", { method: "POST", body });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Summary failed.");
    }
    lastMarkdown = payload.markdown;
    resultHtml.innerHTML = payload.html;
    resultMeta.textContent = `${payload.page_count} PDF pages · ${payload.locator_count} in-text locators · ${payload.model}`;
    resultEl.hidden = false;
    setStatus("Draft ready. Edit before publishing.", true);
  } catch (error) {
    setStatus(error.message || "Summary failed.");
  } finally {
    submitBtn.disabled = false;
  }
});

copyBtn.addEventListener("click", async () => {
  await navigator.clipboard.writeText(lastMarkdown);
  copyBtn.textContent = "Copied";
  setTimeout(() => {
    copyBtn.textContent = "Copy Markdown";
  }, 1500);
});

mdBtn.addEventListener("click", () => {
  downloadBlob(new Blob([lastMarkdown], { type: "text/markdown" }), "interpreting-interpreter-summary.md");
});

docxBtn.addEventListener("click", async () => {
  const response = await fetch("/api/export/docx", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ markdown: lastMarkdown }),
  });
  if (!response.ok) {
    setStatus("Could not export Word document.");
    return;
  }
  const blob = await response.blob();
  downloadBlob(blob, "interpreting-interpreter-summary.docx");
});

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
