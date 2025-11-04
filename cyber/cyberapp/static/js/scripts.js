// static/js/active_sessions
document.addEventListener('DOMContentLoaded', function () {
    // Realtime timers for each active session
    document.querySelectorAll('.session-row').forEach(function (row) {
        const startStr = row.dataset.start;
        const start = new Date(startStr);
        const elapsedEl = row.querySelector('.elapsed');
        const amountEl = row.querySelector('.amount');
        const stkBtn = row.querySelector('.stk-btn');

        function updateTimer() {

            //stop updating if session ended
            if (row.classList.contains('ended-row')) {
                return; //interval will continue but no updates
            }

            const now = new Date();
            let elapsedMs = now - start;

            // Calculate HH:MM:SS
            const hours = Math.floor(elapsedMs / (1000 * 60 * 60));
            const minutes = Math.floor((elapsedMs % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((elapsedMs % (1000 * 60)) / 1000);

            elapsedEl.textContent = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;

            // Amount: 100 KSH per hour (pro-rated)
            const elapsedHours = elapsedMs / (1000 * 60 * 60);
            const amount = Math.round(elapsedHours * 100 * 100) / 100; // 2 decimals
            amountEl.textContent = amount.toFixed(2) + ' KSH';
        }

        // Initial
        updateTimer();
        // Tick every second
        setInterval(updateTimer, 1000);
    });

    // End session function (AJAX to stay on page)
    window.endSession = function (button) {
        if (!confirm('End session?')) return;

        const row = button.closest('.session-row');
        const sessionId = row.dataset.sessionId;
        const studentId = row.dataset.studentId;

        const csrfToken = document.querySelector('meta[name="csrf-Token"]').getAttribute('content');

        fetch(`/end_session/${studentId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken // Assumes CSRF in head or meta
            },
            body: JSON.stringify({ session_id: sessionId })
        })
            .then(response => {
                console.log('Response Status:', response.status);  // Debug: HTTP status
                return response.json();  // Always parse JSON first
            })
            .then(data => {
                console.log('Response Data:', data);  // Debug: Full response
                if (data.status === 'success') {
                    // On success: Update row to "ended" state, enable STK
                    row.classList.remove('session-row');
                    row.classList.add('ended-row');
                    button.textContent = 'Session Ended';
                    button.disabled = true;
                    button.style.background = 'linear-gradient(135deg, #6c757d, #545b62)';
                    const stkBtn = row.querySelector('.stk-btn');
                    stkBtn.disabled = false;
                    stkBtn.classList.remove('stk-btn');
                    stkBtn.classList.add('action-btn');
                    stkBtn.textContent = 'Send STK';
                    stkBtn.onclick = function () {
                        alert('STK Push Logic Here - Integrate M-Pesa/Daraja API'); // Placeholder
                    };
                    row.querySelector('.elapsed').textContent = 'Ended';
                    row.querySelector('.amount').textContent = data.amount + ' KSH'; // Server final amount
                    // Enhanced toast notification
                    showMessage('Session ended successfully. Amount due: ' + data.amount + ' KSH.', 'success');
                } else {
                    showMessage(data.message || 'Error ending session: ' + data.status, 'error');
                }
            })
            .catch(error => {
                console.error('Full Error:', error);  // Debug: Full error object
                showMessage('Network error: ' + (error.message || 'Check console for details'), 'error');
            });
    };

    // Enhanced toast notification function
    function showMessage(text, type) {
        // Remove existing toasts
        document.querySelectorAll('.toast-message').forEach(el => el.remove());

        const messageDiv = document.createElement('div');
        messageDiv.className = `alert alert-${type === 'success' ? 'success' : 'danger'} toast-message`;
        messageDiv.textContent = text;
        messageDiv.style.cssText = `
            position: fixed; top: 120px; right: 20px; z-index: 1000; 
            padding: 15px 20px; border-radius: 6px; color: #155724; 
            max-width: 350px; font-size: 14px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            background: #d4edda; border: 1px solid #c3e6cb;
        `;
        if (type === 'error') {
            messageDiv.style.background = '#f8d7da';
            messageDiv.style.color = '#721c24';
            messageDiv.style.borderColor = '#f5c6cb';
        }
        document.body.appendChild(messageDiv);
        // Auto-remove after 5s
        setTimeout(() => messageDiv.remove(), 5000);
    }
});

// notification auto-hide
// setTimeout(function() {
//     var messages = document.querySelectorAll('.messages');
//     messages.forEach(function(msg) {
//         msg.style.display = 'none';
//     });
// }, 5000);
// end notification auto-hide

document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('profileToggle');
    const dropdown = document.getElementById('profileDropdown');

    toggle.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdown.classList.toggle('show');
    });

    // Hide dropdown when clicking outside
    document.addEventListener('click', () => {
        dropdown.classList.remove('show');
    });
});
