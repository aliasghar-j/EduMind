// Simple Toast Notification System
(function() {
  let toastContainer = null;

  function ensureToastContainer() {
    if (toastContainer) return;
    toastContainer = document.createElement('div');
    toastContainer.className = 'fixed bottom-5 right-5 space-y-2 z-50';
    document.body.appendChild(toastContainer);
  }

  function showToast(message, type = 'info', duration = 3000) {
    ensureToastContainer();

    const toast = document.createElement('div');
    const baseClasses = 'px-4 py-3 rounded-lg shadow-lg text-white';
    const typeClasses = {
      info: 'bg-blue-500',
      success: 'bg-green-500',
      error: 'bg-red-500'
    };

    toast.className = `${baseClasses} ${typeClasses[type] || typeClasses['info']}`;
    toast.textContent = message;

    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.transition = 'opacity 0.5s ease';
      toast.style.opacity = '0';
      setTimeout(() => {
        toast.remove();
        if (toastContainer.children.length === 0) {
            toastContainer.remove();
            toastContainer = null;
        }
      }, 500);
    }, duration);
  }

  window.showToast = showToast;
})();