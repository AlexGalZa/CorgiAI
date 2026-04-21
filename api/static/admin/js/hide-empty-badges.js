// Unfold renders its inline badge wrapper (rounded pill next to tab titles
// and sidebar items) even when the content resolves to an empty string or
// pure whitespace. The result is a small colored pill with nothing inside.
// This script trims text content and hides any badge that has no visible
// characters. A MutationObserver keeps it working through htmx swaps.

(function () {
  var BADGE_SELECTOR = "span.rounded-xs.uppercase";

  function hideIfBlank(el) {
    if (!el) return;
    if (!el.textContent || !el.textContent.trim()) {
      el.style.display = "none";
    }
  }

  function sweep(root) {
    var scope = root && root.querySelectorAll ? root : document;
    var badges = scope.querySelectorAll(BADGE_SELECTOR);
    for (var i = 0; i < badges.length; i++) hideIfBlank(badges[i]);
  }

  function start() {
    sweep(document);
    var obs = new MutationObserver(function (mutations) {
      for (var i = 0; i < mutations.length; i++) {
        var m = mutations[i];
        for (var j = 0; j < m.addedNodes.length; j++) {
          var node = m.addedNodes[j];
          if (node.nodeType === 1) sweep(node);
        }
      }
    });
    obs.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
