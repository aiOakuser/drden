// Global site scripts
(function () {
  "use strict";

  // Graceful image error fallback: swap to placeholder if missing
  function addImageFallbacks() {
    var placeholder = (window.STATIC_PLACEHOLDER && window.STATIC_PLACEHOLDER.image) || (window.STATIC_URL ? window.STATIC_URL + "images/placehold.png" : "/static/images/placehold.png");
    document.querySelectorAll('img').forEach(function (img) {
      if (img.dataset && img.dataset.noFallback === "true") return;
      img.addEventListener('error', function onError() {
        if (img.src.endsWith('/images/placehold.png')) return; // don't loop
        img.removeEventListener('error', onError);
        img.src = placeholder;
      }, { once: true });
    });
  }

  // Popup helpers if used in templates
  window.openPopup = window.openPopup || function (index) {
    var popup = document.getElementById('popup');
    if (!popup) return;
    popup.classList.add('show');
  };

  window.closePopup = window.closePopup || function () {
    var popup = document.getElementById('popup');
    if (!popup) return;
    var video = document.getElementById('popup-video');
    if (video && typeof video.pause === 'function') video.pause();
    popup.classList.remove('show');
  };

  window.changePopup = window.changePopup || function (delta) {
    // no-op shim; individual pages implement navigation
  };

  document.addEventListener('DOMContentLoaded', function () {
    addImageFallbacks();
  });
})();
