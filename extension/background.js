const BACKEND_URL = "http://localhost:8000";

// Set up context menu on install
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "save-to-neko",
    title: "Save to Neko Vault",
    contexts: ["selection"]
  });
});

// Listen for context menu click
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "save-to-neko" && info.selectionText) {
    const noteData = {
      url: tab.url,
      title: tab.title || "Untitled Page",
      content: info.selectionText,
      tags: ["highlight"]
    };
    saveNote(noteData);
  }
});

// Listen for messages from popup or content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "saveNote") {
    saveNote(request.data).then(sendResponse);
    return true; // Keep message channel open for async response
  } else if (request.action === "checkPageStatus") {
    checkPageStatus(request.url).then(sendResponse);
    return true;
  } else if (request.action === "getSyncQueue") {
    getSyncQueue().then(sendResponse);
    return true;
  } else if (request.action === "triggerSync") {
    syncQueue().then(sendResponse);
    return true;
  }
});

// Check if page is already in the vault
async function checkPageStatus(url) {
  try {
    const res = await fetch(`${BACKEND_URL}/api/notes`);
    if (!res.ok) return { saved: false };
    const notes = await res.json();
    const match = notes.find(n => n.url === url);
    return { saved: !!match, note: match || null };
  } catch (err) {
    // If backend is down, check offline queue
    const queue = await getSyncQueue();
    const match = queue.find(item => item.url === url);
    return { saved: !!match, note: match || null, offline: true };
  }
}

// Save a note (handles offline queueing)
async function saveNote(noteData) {
  try {
    const res = await fetch(`${BACKEND_URL}/api/notes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(noteData)
    });
    if (res.ok) {
      const data = await res.json();
      return { success: true, status: "saved", noteId: data.note_id };
    } else {
      throw new Error("Server error");
    }
  } catch (err) {
    // Queue offline
    await queueOffline(noteData);
    return { success: true, status: "queued", message: "Neko server offline. Saved to offline queue." };
  }
}

// Get the offline sync queue
function getSyncQueue() {
  return new Promise((resolve) => {
    chrome.storage.local.get({ syncQueue: [] }, (result) => {
      resolve(result.syncQueue);
    });
  });
}

// Queue note offline
async function queueOffline(noteData) {
  const queue = await getSyncQueue();
  // Avoid duplicate URLs in offline queue
  if (!queue.some(item => item.url === noteData.url)) {
    queue.push(noteData);
    await new Promise(resolve => {
      chrome.storage.local.set({ syncQueue: queue }, resolve);
    });
  }
}

// Sync queue to backend
async function syncQueue() {
  const queue = await getSyncQueue();
  if (queue.length === 0) return { synced: 0, total: 0 };

  let syncedCount = 0;
  const remaining = [];

  for (const noteData of queue) {
    try {
      const res = await fetch(`${BACKEND_URL}/api/notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(noteData)
      });
      if (res.ok) {
        syncedCount++;
      } else {
        remaining.push(noteData);
      }
    } catch (err) {
      remaining.push(noteData);
    }
  }

  await new Promise(resolve => {
    chrome.storage.local.set({ syncQueue: remaining }, resolve);
  });

  return { synced: syncedCount, total: queue.length };
}

// Periodically attempt to sync when background script runs
setInterval(syncQueue, 60000); // Check every minute
