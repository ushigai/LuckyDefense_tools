import { translateDomTree } from "./i18n.js";

const RELEASE_NOTES_DISMISSED_VERSION_KEY = "dps_sim1.releaseNotes.dismissedVersion";
const VERSION_RE = /(v\d+(?:\.\d+)+)/i;

function extractVersion(text) {
  return String(text ?? "").match(VERSION_RE)?.[1] ?? "";
}

function readDismissedVersion() {
  try {
    return String(window.localStorage.getItem(RELEASE_NOTES_DISMISSED_VERSION_KEY) ?? "");
  } catch {
    return "";
  }
}

function writeDismissedVersion(version) {
  try {
    window.localStorage.setItem(RELEASE_NOTES_DISMISSED_VERSION_KEY, version);
  } catch {
    // ignore
  }
}

function clearDismissedVersion() {
  try {
    window.localStorage.removeItem(RELEASE_NOTES_DISMISSED_VERSION_KEY);
  } catch {
    // ignore
  }
}

function getCurrentVersion() {
  return extractVersion(document.getElementById("appVersionText")?.textContent);
}

function findReleaseNoteEntry(version) {
  if (!version) return null;

  const entries = Array.from(document.querySelectorAll(".release-notes .rn-body > div"));
  return entries.find((entry) => {
    const entryVersion = extractVersion(entry.querySelector(".rn-ver")?.textContent);
    return entryVersion === version;
  }) ?? null;
}

function buildModalContent(entry) {
  const fragment = document.createDocumentFragment();
  fragment.appendChild(entry.cloneNode(true));
  return fragment;
}

export function initReleaseNotesPopup() {
  const modalEl = document.getElementById("releaseNotesModal");
  const contentEl = document.getElementById("releaseNotesModalContent");
  const checkboxEl = document.getElementById("releaseNotesDoNotShow");
  if (!modalEl || !contentEl || !checkboxEl) return;
  if (typeof window.bootstrap?.Modal !== "function") return;

  const currentVersion = getCurrentVersion();
  if (!currentVersion) return;

  const releaseNoteEntry = findReleaseNoteEntry(currentVersion);
  if (!releaseNoteEntry) return;
  // Suppress only the current app version so newer releases can be shown again.
  if (readDismissedVersion() === currentVersion) return;

  contentEl.replaceChildren(buildModalContent(releaseNoteEntry));
  translateDomTree(contentEl);

  checkboxEl.checked = false;
  const modal = new window.bootstrap.Modal(modalEl);
  modalEl.addEventListener("hidden.bs.modal", () => {
    if (checkboxEl.checked) {
      writeDismissedVersion(currentVersion);
      return;
    }
    if (readDismissedVersion() === currentVersion) {
      clearDismissedVersion();
    }
  }, { once: true });
  modal.show();
}
