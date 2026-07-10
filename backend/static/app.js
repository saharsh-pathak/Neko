const API_BASE = "http://localhost:8000/api";

document.addEventListener("DOMContentLoaded", () => {
  // Navigation elements
  const navItems = document.querySelectorAll(".nav-item");
  const tabs = document.querySelectorAll(".tab-content");
  
  // Chat elements
  const mainSearchInput = document.getElementById("main-search-input");
  const mainSearchBtn = document.getElementById("main-search-btn");
  const searchResultArea = document.getElementById("search-result-area");
  const aiAnswerText = document.getElementById("ai-answer-text");
  const sourcesContainer = document.getElementById("sources-container");

  // Vault Browser elements
  const vaultItemsContainer = document.getElementById("vault-items-container");
  const vaultFilterInput = document.getElementById("vault-filter-input");
  const vaultTagFilter = document.getElementById("vault-tag-filter");

  // Active Recall elements
  const dueBadge = document.getElementById("due-badge");
  const dueCountText = document.getElementById("due-count-text");
  const startSessionBtn = document.getElementById("start-session-btn");
  const recallWelcomeView = document.getElementById("recall-welcome-view");
  const quizSessionView = document.getElementById("quiz-session-view");
  const quizNoteTag = document.getElementById("quiz-note-tag");
  const quizNoteTitle = document.getElementById("quiz-note-title");
  const quizQuestionText = document.getElementById("quiz-question-text");
  const quizHintText = document.getElementById("quiz-hint-text");
  const quizInputBox = document.getElementById("quiz-input-box");
  const quizUserAnswer = document.getElementById("quiz-user-answer");
  const submitAnswerBtn = document.getElementById("submit-answer-btn");
  const quizResultBox = document.getElementById("quiz-result-box");
  const gradeBadgeEl = document.getElementById("grade-badge-el");
  const gradeMessageEl = document.getElementById("grade-message-el");
  const gradeFeedbackText = document.getElementById("grade-feedback-text");
  const gradeCorrectAnswer = document.getElementById("grade-correct-answer");
  const nextQuizBtn = document.getElementById("next-quiz-btn");

  // Modal elements
  const noteModal = document.getElementById("note-modal");
  const modalTitle = document.getElementById("modal-title");
  const modalUrl = document.getElementById("modal-url");
  const modalTags = document.getElementById("modal-tags");
  const modalContentBody = document.getElementById("modal-content-body");
  const closeModalBtn = document.getElementById("close-modal-btn");

  // Global Session State
  let allNotes = [];
  let currentQuizNote = null;
  let currentQuizQuestion = "";

  // 1. Tab Switching
  navItems.forEach(item => {
    item.addEventListener("click", () => {
      const tabId = item.dataset.tab;
      
      navItems.forEach(nav => nav.classList.remove("active"));
      tabs.forEach(tab => tab.classList.remove("active"));
      
      item.classList.add("active");
      document.getElementById(`tab-${tabId}`).classList.add("active");

      // Load tab-specific data
      if (tabId === "vault") {
        loadVaultData();
      } else if (tabId === "recall") {
        loadRecallStats();
      }
    });
  });

  // Check backend server status & update due count on startup
  async function checkServerStatus() {
    const statusEl = document.getElementById("server-status");
    try {
      const res = await fetch(`${API_BASE}/notes`);
      if (res.ok) {
        statusEl.className = "status-indicator online";
        statusEl.nextElementSibling.textContent = "Local Server Online";
        loadRecallStats(); // Populate badge on load
      } else {
        throw new Error();
      }
    } catch (e) {
      statusEl.className = "status-indicator";
      statusEl.nextElementSibling.textContent = "Local Server Offline";
    }
  }

  // 2. Chat & RAG Search
  mainSearchBtn.addEventListener("click", async () => {
    const query = mainSearchInput.value.trim();
    if (!query) return;

    mainSearchBtn.disabled = true;
    mainSearchBtn.textContent = "Searching...";
    searchResultArea.style.display = "block";
    aiAnswerText.innerHTML = "<p class='thinking'>Neko is thinking...</p>";
    sourcesContainer.innerHTML = "";

    try {
      const res = await fetch(`${API_BASE}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query })
      });

      if (res.ok) {
        const data = await res.json();
        // Render markdown/text response (escaped for safety)
        aiAnswerText.textContent = data.answer;
        
        // Render sources
        if (data.results && data.results.length > 0) {
          data.results.forEach(res => {
            const note = res.note;
            const card = document.createElement("div");
            card.className = "source-card";
            card.innerHTML = `
              <h5>${escapeHtml(note.title)}</h5>
              <div class="source-meta">
                <span>Score: ${res.colbert_score.toFixed(2)}</span>
                <span>Tag: ${note.tags[0] || 'none'}</span>
              </div>
            `;
            card.addEventListener("click", () => showNoteModal(note));
            sourcesContainer.appendChild(card);
          });
        } else {
          sourcesContainer.innerHTML = "<p>No specific source references found.</p>";
        }
      } else {
        aiAnswerText.textContent = "Search failed. Check local server logs.";
      }
    } catch (err) {
      aiAnswerText.textContent = "Error connecting to backend server. Make sure FastAPI is running on port 8000.";
    } finally {
      mainSearchBtn.disabled = false;
      mainSearchBtn.innerHTML = `
        <span>Ask Neko</span>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="22" y1="22" x2="16.65" y2="16.65"/><circle cx="11" cy="11" r="8"/></svg>
      `;
    }
  });

  mainSearchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") mainSearchBtn.click();
  });

  // 3. Vault Browser Logic
  async function loadVaultData() {
    try {
      const res = await fetch(`${API_BASE}/notes`);
      if (res.ok) {
        allNotes = await res.json();
        renderVaultGrid(allNotes);
        populateTagFilter();
      }
    } catch (err) {
      vaultItemsContainer.innerHTML = "<p class='error-msg'>Failed to load notes.</p>";
    }
  }

  function renderVaultGrid(notesList) {
    vaultItemsContainer.innerHTML = "";
    if (notesList.length === 0) {
      vaultItemsContainer.innerHTML = "<p>Your vault is currently empty.</p>";
      return;
    }

    notesList.forEach(note => {
      const card = document.createElement("div");
      card.className = "vault-card";
      
      const dateStr = new Date(note.timestamp).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
      
      card.innerHTML = `
        <div class="vault-card-header">
          <span class="vault-card-date">${dateStr}</span>
          <button class="btn-delete" title="Delete note">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
          </button>
        </div>
        <div class="vault-card-body">
          <h3>${escapeHtml(note.title)}</h3>
          <p>${escapeHtml(note.content)}</p>
        </div>
        <div class="vault-card-tags">
          ${note.tags.map(t => `<span class="tag-badge">${escapeHtml(t)}</span>`).join("")}
        </div>
      `;

      // Card body clicks open modal
      card.querySelector(".vault-card-body").addEventListener("click", () => showNoteModal(note));
      card.querySelector(".vault-card-tags").addEventListener("click", () => showNoteModal(note));
      
      // Delete button click
      card.querySelector(".btn-delete").addEventListener("click", (e) => {
        e.stopPropagation();
        if (confirm(`Are you sure you want to delete "${note.title}"?`)) {
          deleteNoteCall(note.id);
        }
      });

      vaultItemsContainer.appendChild(card);
    });
  }

  async function deleteNoteCall(noteId) {
    try {
      const res = await fetch(`${API_BASE}/notes/${noteId}`, { method: "DELETE" });
      if (res.ok) {
        loadVaultData();
        loadRecallStats();
      }
    } catch (e) {
      alert("Failed to delete note.");
    }
  }

  function populateTagFilter() {
    fetch(`${API_BASE}/tags`)
      .then(res => res.json())
      .then(tags => {
        const currentVal = vaultTagFilter.value;
        vaultTagFilter.innerHTML = '<option value="">All Tags</option>';
        tags.forEach(tag => {
          const opt = document.createElement("option");
          opt.value = tag;
          opt.textContent = tag;
          vaultTagFilter.appendChild(opt);
        });
        vaultTagFilter.value = currentVal;
      });
  }

  // Filter vault items locally on input
  function filterVaultItems() {
    const textQuery = vaultFilterInput.value.toLowerCase();
    const tagQuery = vaultTagFilter.value.toLowerCase();

    const filtered = allNotes.filter(note => {
      const textMatch = note.title.toLowerCase().includes(textQuery) || note.content.toLowerCase().includes(textQuery);
      const tagMatch = !tagQuery || note.tags.some(t => t.toLowerCase() === tagQuery);
      return textMatch && tagMatch;
    });

    renderVaultGrid(filtered);
  }

  vaultFilterInput.addEventListener("input", filterVaultItems);
  vaultTagFilter.addEventListener("change", filterVaultItems);

  // 4. Modal Logic
  function showNoteModal(note) {
    modalTitle.textContent = note.title;
    modalUrl.href = note.url;
    modalUrl.textContent = note.url;
    modalTags.innerHTML = note.tags.map(t => `<span class="tag-badge">${escapeHtml(t)}</span>`).join("");
    modalContentBody.textContent = note.content;
    noteModal.style.display = "flex";
  }

  closeModalBtn.addEventListener("click", () => {
    noteModal.style.display = "none";
  });

  window.addEventListener("click", (e) => {
    if (e.target === noteModal) {
      noteModal.style.display = "none";
    }
  });

  // 5. Active Recall Spaced Repetition Logic
  async function loadRecallStats() {
    try {
      const res = await fetch(`${API_BASE}/quiz/next`);
      if (res.ok) {
        const data = await res.json();
        const dueCount = data.due_count;
        
        // Update sidebar badge
        if (dueCount > 0) {
          dueBadge.textContent = dueCount;
          dueBadge.style.display = "inline-block";
          startSessionBtn.disabled = false;
        } else {
          dueBadge.style.display = "none";
          startSessionBtn.disabled = true;
        }
        
        dueCountText.textContent = dueCount;
      }
    } catch (e) {
      dueBadge.style.display = "none";
    }
  }

  // Start Session
  startSessionBtn.addEventListener("click", async () => {
    recallWelcomeView.style.display = "none";
    quizSessionView.style.display = "block";
    loadNextQuizCard();
  });

  async function loadNextQuizCard() {
    quizInputBox.style.display = "block";
    quizResultBox.style.display = "none";
    quizUserAnswer.value = "";
    quizQuestionText.textContent = "Generating question...";
    quizHintText.textContent = "";
    submitAnswerBtn.disabled = true;

    try {
      const res = await fetch(`${API_BASE}/quiz/next`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      currentQuizNote = data.note;

      if (!currentQuizNote) {
        // Finished everything!
        recallWelcomeView.style.display = "grid";
        quizSessionView.style.display = "none";
        loadRecallStats();
        alert("Well done! You've reviewed all due knowledge cards for now.");
        return;
      }

      // Populate card metadata
      quizNoteTitle.textContent = currentQuizNote.title;
      quizNoteTag.textContent = currentQuizNote.tags[0] || "Vault Note";

      // Call API to generate LLM question
      const qRes = await fetch(`${API_BASE}/quiz/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note_id: currentQuizNote.id })
      });

      if (qRes.ok) {
        const qData = await qRes.json();
        currentQuizQuestion = qData.question;
        quizQuestionText.textContent = qData.question;
        quizHintText.textContent = qData.hint ? `Hint: ${qData.hint}` : "No hint available.";
        submitAnswerBtn.disabled = false;
      } else {
        throw new Error();
      }
    } catch (e) {
      quizQuestionText.textContent = "Failed to load quiz question. Backend offline.";
      quizHintText.textContent = "Ensure local server is running.";
    }
  }

  // Submit Answer
  submitAnswerBtn.addEventListener("click", async () => {
    const answer = quizUserAnswer.value.trim();
    if (!answer) return;

    submitAnswerBtn.disabled = true;
    submitAnswerBtn.textContent = "Grading...";

    try {
      const res = await fetch(`${API_BASE}/quiz/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          note_id: currentQuizNote.id,
          question: currentQuizQuestion,
          user_answer: answer
        })
      });

      if (res.ok) {
        const data = await res.json();
        const evalResult = data.evaluation;
        const rating = evalResult.rating;

        // Render grading block
        quizInputBox.style.display = "none";
        quizResultBox.style.display = "block";

        // Style score badge based on quality
        gradeBadgeEl.textContent = `Score: ${rating}/5`;
        if (rating >= 4) {
          gradeBadgeEl.className = "grade-badge"; // Success (green)
          gradeMessageEl.textContent = "Great memory!";
        } else if (rating === 3) {
          gradeBadgeEl.className = "grade-badge avg"; // Warning (yellow)
          gradeMessageEl.textContent = "Close, but need study.";
        } else {
          gradeBadgeEl.className = "grade-badge poor"; // Danger (red)
          gradeMessageEl.textContent = "Forgot or incorrect.";
        }

        gradeFeedbackText.textContent = evalResult.feedback;
        gradeCorrectAnswer.textContent = evalResult.correct_answer;
      } else {
        alert("Failed to submit answer to server.");
      }
    } catch (e) {
      alert("Error grading answer.");
    } finally {
      submitAnswerBtn.disabled = false;
      submitAnswerBtn.textContent = "Submit Answer";
    }
  });

  // Next Question
  nextQuizBtn.addEventListener("click", () => {
    loadNextQuizCard();
  });

  // Helper: Escape HTML string
  function escapeHtml(text) {
    if (!text) return "";
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Startup checks
  checkServerStatus();
  setInterval(checkServerStatus, 5000); // Poll status every 5 seconds
});
