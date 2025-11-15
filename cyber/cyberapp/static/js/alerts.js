const SWEETALERT_SRC = 'https://cdn.jsdelivr.net/npm/sweetalert2@11';
let sweetAlertPromise = null;

function loadSweetAlert() {
  if (window.Swal) {
    return Promise.resolve();
  }
  if (!sweetAlertPromise) {
    sweetAlertPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = SWEETALERT_SRC;
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error('Failed to load SweetAlert2'));
      document.head.appendChild(script);
    });
  }
  return sweetAlertPromise;
}

function mapLevelToIcon(level) {
  switch (level) {
    case 'success':
      return 'success';
    case 'warning':
      return 'warning';
    case 'error':
    case 'danger':
      return 'error';
    default:
      return 'info';
  }
}

function showAlert(message, level = 'info') {
  if (!message) return;
  loadSweetAlert()
    .then(() => {
      Swal.fire({
        icon: mapLevelToIcon(level),
        title: message,
        confirmButtonText: 'OK',
        confirmButtonColor: '#2563eb',
        backdrop: true,
      });
    })
    .catch((error) => {
      console.error(error);
      alert(message);
    });
}

window.showAlert = showAlert;

document.addEventListener('DOMContentLoaded', () => {
  const messageContainers = document.querySelectorAll('.messages');
  const alerts = [];

  messageContainers.forEach((container) => {
    container.querySelectorAll('li').forEach((item) => {
      const text = item.textContent.trim();
      let level = 'info';

      if (item.classList.contains('alert-success')) {
        level = 'success';
      } else if (item.classList.contains('alert-warning')) {
        level = 'warning';
      } else if (
        item.classList.contains('alert-danger') ||
        item.classList.contains('alert-error')
      ) {
        level = 'error';
      }

      if (text) {
        alerts.push({ text, level });
      }
    });

    container.style.display = 'none';
  });

  if (alerts.length) {
    // show the most recent message so modals don't stack
    const latest = alerts[alerts.length - 1];
    showAlert(latest.text, latest.level);
  }
});

