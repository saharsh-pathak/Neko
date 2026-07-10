const BACKEND_URL = "http://localhost:8000";

document.addEventListener("DOMContentLoaded", async () => {
  const statusBadge = document.getElementById("status-badge");
  const pageTitleEl = document.getElementById("page-title");
  const tagInput = document.getElementById("tag-input");
  const voiceTagsBtn = document.getElementById("voice-tags-btn");
  const voiceStatus = document.getElementById("voice-status");
  const saveBtn = document.getElementById("save-btn");
  const chatInput = document.getElementById("chat-input");
  const chatSendBtn = document.getElementById("chat-send-btn");
  const chatResponse = document.getElementById("chat-response");

  let currentTab = null;
  let isSaved = false;

  // 1. Get current tab info
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tabs && tabs[0]) {
    currentTab = tabs[0];
    pageTitleEl.textContent = currentTab.title || "Untitled Page";
    updatePageStatus();
  }

  // Check if page is saved
  async function updatePageStatus() {
    if (!currentTab) return;
    chrome.runtime.sendMessage(
      { action: "checkPageStatus", url: currentTab.url },
      (response) => {
        if (chrome.runtime.lastError) {
          statusBadge.textContent = "Offline";
          statusBadge.className = "status-badge";
          return;
        }
        if (response && response.saved) {
          isSaved = true;
          statusBadge.textContent = response.offline ? "Offline (Saved)" : "Saved";
          statusBadge.className = "status-badge saved";
          saveBtn.textContent = "Update Saved Page";
          if (response.note && response.note.tags) {
            tagInput.value = response.note.tags.join(", ");
          }
        } else {
          isSaved = false;
          statusBadge.textContent = "Unsaved";
          statusBadge.className = "status-badge";
          saveBtn.textContent = "Save This Page";
        }
      }
    );
  }

  // 2. Save Button Click
  saveBtn.addEventListener("click", async () => {
    if (!currentTab) return;
    saveBtn.disabled = true;
    saveBtn.textContent = "Saving...";
    statusBadge.textContent = "Saving...";

    // Extract content from page
    chrome.tabs.sendMessage(currentTab.id, { action: "extractContent" }, async (pageData) => {
      let data = pageData;
      if (chrome.runtime.lastError || !pageData) {
        // Fallback if content script is not loaded
        data = {
          title: currentTab.title,
          url: currentTab.url,
          content: "Could not extract article content. Bookmark saved."
        };
      }

      // Parse tags
      const tags = tagInput.value
        .split(",")
        .map(t => t.trim())
        .filter(t => t.length > 0);

      data.tags = tags;

      // Send to background to save (handles offline queueing)
      chrome.runtime.sendMessage({ action: "saveNote", data }, (response) => {
        saveBtn.disabled = false;
        if (response && response.success) {
          if (response.status === "saved") {
            isSaved = true;
            statusBadge.textContent = "Saved";
            statusBadge.className = "status-badge saved";
            saveBtn.textContent = "Update Saved Page";
          } else {
            statusBadge.textContent = "Queued";
            statusBadge.className = "status-badge queued";
            saveBtn.textContent = "Queued Offline";
            voiceStatus.textContent = response.message;
          }
        } else {
          statusBadge.textContent = "Error";
          saveBtn.textContent = "Retry Saving";
        }
      });
    });
  });

  // 3. Voice Tagging (Web Speech API)
  let recognition = null;
  if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      voiceTagsBtn.classList.add("recording");
      voiceStatus.textContent = "Listening for tags...";
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      // Clean and split words by spaces/commas to add as tags
      const newTags = transcript
        .replace(/[^a-zA-Z0-9\s,]/g, '')
        .split(/[\s,]+/)
        .filter(t => t.length > 0)
        .join(", ");
        
      if (newTags) {
        if (tagInput.value) {
          tagInput.value = tagInput.value + ", " + newTags;
        } else {
          tagInput.value = newTags;
        }
      }
      voiceStatus.textContent = `Added: "${transcript}"`;
    };

    recognition.onerror = (event) => {
      voiceStatus.textContent = "Voice error. Try again.";
      voiceTagsBtn.classList.remove("recording");
    };

    recognition.onend = () => {
      voiceTagsBtn.classList.remove("recording");
    };
  } else {
    voiceTagsBtn.style.display = "none";
  }

  voiceTagsBtn.addEventListener("click", () => {
    if (recognition) {
      if (voiceTagsBtn.classList.contains("recording")) {
        recognition.stop();
      } else {
        recognition.start();
      }
    }
  });

  // 4. Chat Q&A Section
  chatSendBtn.addEventListener("click", async () => {
    const query = chatInput.value.trim();
    if (!query) return;

    chatSendBtn.disabled = true;
    chatInput.disabled = true;
    chatResponse.style.display = "block";
    chatResponse.textContent = "Thinking...";

    try {
      // 1. Ensure page is saved first if it isn't, so it is in the context
      if (!isSaved && currentTab) {
        chatResponse.textContent = "Saving page to context first...";
        await new Promise((resolve, reject) => {
          chrome.tabs.sendMessage(currentTab.id, { action: "extractContent" }, (pageData) => {
            let data = pageData || {
              title: currentTab.title,
              url: currentTab.url,
              content: "Bookmark saved."
            };
            const tags = tagInput.value.split(",").map(t => t.strip()).filter(t => t.length > 0);
            data.tags = [...tags, "chat-auto-save"];

            chrome.runtime.sendMessage({ action: "saveNote", data }, (response) => {
              if (response && response.success) {
                isSaved = true;
                updatePageStatus();
                resolve();
              } else {
                reject(new Error("Auto-save failed"));
              }
            });
          });
        });
      }

      chatResponse.textContent = "Searching vault & generating answer...";
      
      // 2. Perform search
      const res = await fetch(`${BACKEND_URL}/api/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query })
      });

      if (res.ok) {
        const result = await res.json();
        chatResponse.textContent = result.answer;
      } else {
        chatResponse.textContent = "Error: Neko server returned an error.";
      }
    } catch (err) {
      chatResponse.textContent = "Error connecting to Neko backend. Ensure uvicorn is running.";
    } finally {
      chatSendBtn.disabled = false;
      chatInput.disabled = false;
      chatInput.value = "";
    }
  });

  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      chatSendBtn.click();
    }
  });
});

// Helper
String.prototype.strip = function() {
  return this.replace(/^\s+|\s+$/g, '');
};
