// Listen for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "extractContent") {
    const pageData = extractPageContent();
    sendResponse(pageData);
  }
});

// Check if page is saved on load
(function init() {
  chrome.runtime.sendMessage(
    { action: "checkPageStatus", url: window.location.href },
    (response) => {
      if (response && response.saved) {
        showRevisitBadge(response.note);
      }
    }
  );
})();

// Function to extract text content
function extractPageContent() {
  const title = document.title || "Untitled Page";
  const url = window.location.href;
  
  // Find selected text first, if any
  const selection = window.getSelection().toString().strip();
  if (selection) {
    return { title, url, content: selection };
  }
  
  // Otherwise, extract main paragraphs to avoid nav/footer noise
  const paragraphs = Array.from(document.querySelectorAll("p, h1, h2, h3, h4, article"))
    .map(el => el.innerText.trim())
    .filter(text => text.length > 20); // Filter out short strings
    
  // Combine up to a reasonable word count limit (e.g. 5000 words)
  const fullText = paragraphs.join("\n\n");
  
  return {
    title,
    url,
    content: fullText || document.body.innerText || ""
  };
}

// Helper to strip whitespace
String.prototype.strip = function() {
  return this.replace(/^\s+|\s+$/g, '');
};

// Inject revisit badge
function showRevisitBadge(note) {
  // Check if badge already exists
  if (document.getElementById("neko-revisit-badge")) return;
  
  const badge = document.createElement("div");
  badge.id = "neko-revisit-badge";
  
  // Style the badge with a premium glassmorphic dark look
  Object.assign(badge.style, {
    position: "fixed",
    bottom: "20px",
    right: "20px",
    zIndex: "999999",
    padding: "10px 14px",
    background: "rgba(20, 20, 20, 0.85)",
    backdropFilter: "blur(8px)",
    color: "#fff",
    border: "1px solid rgba(255, 255, 255, 0.15)",
    borderRadius: "12px",
    fontFamily: "system-ui, -apple-system, sans-serif",
    fontSize: "13px",
    fontWeight: "600",
    display: "flex",
    alignItems: "center",
    gap: "8px",
    boxShadow: "0 4px 20px rgba(0, 0, 0, 0.3)",
    cursor: "pointer",
    transition: "transform 0.2s ease, opacity 0.2s ease",
    userSelect: "none"
  });
  
  // Add a cute Neko icon using SVG
  badge.innerHTML = `
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
      <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8z"/>
      <path d="M12 8v4l3 3"/>
    </svg>
    <span>Saved in Neko</span>
  `;
  
  // Hover effects
  badge.addEventListener("mouseenter", () => {
    badge.style.transform = "scale(1.05)";
    badge.style.border = "1px solid rgba(167, 139, 250, 0.5)";
  });
  badge.addEventListener("mouseleave", () => {
    badge.style.transform = "scale(1)";
    badge.style.border = "1px solid rgba(255, 255, 255, 0.15)";
  });
  
  // Quick click to show review state
  badge.addEventListener("click", () => {
    const nextDate = note.review ? note.review.next_review_date : "today";
    alert(`Neko Vault:\n"${note.title}"\nNext review scheduled for: ${nextDate}`);
  });
  
  document.body.appendChild(badge);
}
