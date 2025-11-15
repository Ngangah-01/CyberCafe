// static/js/active_sessions
document.addEventListener('DOMContentLoaded', function () {
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfMeta ? csrfMeta.getAttribute('content') : null;

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
        const row = button.closest('.session-row');
        const sessionId = row.dataset.sessionId;
        const studentId = row.dataset.studentId;
        const studentName = row.cells[0].textContent.trim();

        const confirmPromise = window.showConfirm
            ? window.showConfirm(
                `This will stop the timer for ${studentName} and calculate the final bill.`,
                {
                    title: 'End session?',
                    confirmText: 'Yes, end it',
                    cancelText: 'No, keep running',
                    icon: 'warning',
                }
              )
            : Promise.resolve(window.confirm('End session?'));

        confirmPromise.then((confirmed) => {
            if (!confirmed) return;

            if (!csrfToken) {
                showMessage('CSRF token missing. Refresh the page.', 'error');
                console.error('No CSRF token found');
                return;
            }

            fetch(`/end_session/${studentId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ session_id: sessionId })
            })
            .then(response => {
                if (!response.ok) {
                    return response.text().then(text => {
                        console.error('Error Response Body:', text.substring(0, 200) + '...');
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    row.classList.remove('session-row');
                    row.classList.add('ended-row');
                    button.textContent = 'Session Ended';
                    button.disabled = true;
                    button.style.background = 'linear-gradient(135deg, #6c757d, #545b62)';
                    const stkBtn = row.querySelector('.stk-btn');
                    if (stkBtn) {
                        stkBtn.disabled = false;
                        stkBtn.classList.add('action-btn');
                        stkBtn.textContent = 'Send STK';
                    }
                    row.querySelector('.elapsed').textContent = 'Ended';
                    row.querySelector('.amount').textContent = data.amount + ' KSH';
                    showMessage(`Session ended for ${studentName}. Amount due: ${data.amount} KSH.`, 'success');
                } else {
                    showMessage(data.message || 'Error ending session: ' + data.status, 'error');
                }
            })
            .catch(error => {
                console.error('Full Error:', error);
                showMessage('Network error: ' + (error.message || 'Check console for details'), 'error');
            });
        });
    };

    window.sendSTK = function (button) {
        if (button.disabled) {
            showMessage('End the session first to send an STK push.', 'error');
            return;
        }

        const row = button.closest('tr');
        const sessionId = row.dataset.sessionId;
        let defaultPhone = row.dataset.phone || '';
        if (defaultPhone && defaultPhone.length === 9 && defaultPhone.startsWith('7')) {
            defaultPhone = `0${defaultPhone}`;
        }

        const phone = prompt('Enter the customer phone number (07xx or 2547xx):', defaultPhone);
        if (phone === null) {
            return; // user cancelled
        }

        if (!phone.trim()) {
            showMessage('Phone number cannot be empty.', 'error');
            return;
        }

        if (!csrfToken) {
            showMessage('CSRF token missing. Refresh the page.', 'error');
            return;
        }

        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = 'Sending...';

        fetch(`/sessions/${sessionId}/stk/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ phone_number: phone })
        })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.message || 'STK push failed');
                    });
                }
                return response.json();
            })
            .then(data => {
                showMessage(data.message || 'STK push sent.', 'success');
                button.textContent = 'STK Sent';
            })
            .catch(error => {
                showMessage(error.message || 'Failed to send STK push.', 'error');
                button.disabled = false;
                button.textContent = originalText;
            });
    };
    // Enhanced toast notification function
    function showMessage(text, type) {
        if (window.showToast) {
            window.showToast(text, type === 'success' ? 'success' : type === 'error' ? 'error' : 'info');
            return;
        }
        alert(text);
    }
});

// notification auto-hide
setTimeout(function() {
    var messages = document.querySelectorAll('.messages');
    messages.forEach(function(msg) {
        msg.style.display = 'none';
    });
}, 5000);
// end notification auto-hide

document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('profileToggle');
    const dropdown = document.getElementById('profileDropdown');

    if (toggle && dropdown) {
        toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.classList.toggle('show');
        });

        // Hide dropdown when clicking outside
        document.addEventListener('click', () => {
            dropdown.classList.remove('show');
        });
    }
});


// // Global variables for modal
// let currentSessionId = null;

// // Show STK Modal
// function sendSTK(btn) {
//     const row = btn.closest('tr');
//     currentSessionId = row.dataset.sessionId;
//     document.getElementById('sessionIdDisplay').textContent = currentSessionId;
//     document.getElementById('phoneNumber').value = '';  // Clear input
//     document.getElementById('stkModal').style.display = 'block';
// }

// // Close STK Modal
// function closeSTKModal() {
//     document.getElementById('stkModal').style.display = 'none';
//     currentSessionId = null;
// }

// // Handle form submit and API call
// document.addEventListener('DOMContentLoaded', function() {
//     const stkForm = document.getElementById('stkForm');
//     stkForm.addEventListener('submit', function(e) {
//         e.preventDefault();
        
//         const phoneNumber = document.getElementById('phoneNumber').value.trim();
//         if (!phoneNumber) {
//             alert('Please enter a phone number.');
//             return;
//         }

//         // Disable send button
//         const sendBtn = stkForm.querySelector('.send-btn');
//         sendBtn.disabled = true;
//         sendBtn.textContent = 'Sending...';

//         // POST to Django view
//         fetch('/send-stk/', {
//             method: 'POST',
//             headers: {
//                 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
//                 'Content-Type': 'application/x-www-form-urlencoded',
//             },
//             body: new URLSearchParams({
//                 'session_id': currentSessionId,
//                 'phone_number': phoneNumber
//             })
//         })
//         .then(response => response.json())
//         .then(data => {
//             if (data.success) {
//                 alert(data.message);  // Or use a toast notification
//                 closeSTKModal();
//                 // Optionally update UI: e.g., disable button or change text to "Sent"
//                 const btn = document.querySelector(`[data-session-id="${currentSessionId}"] .stk-btn`);
//                 btn.textContent = 'STK Sent';
//                 btn.disabled = true;
//                 btn.classList.add('sent');  // Add CSS class for styling
//             } else {
//                 alert('Error: ' + (data.error || data.message));
//             }
//         })
//         .catch(error => {
//             alert('Network error: ' + error);
//         })
//         .finally(() => {
//             sendBtn.disabled = false;
//             sendBtn.textContent = 'Send STK';
//         });
//     });

//     // Close modal on X click or outside
//     const modal = document.getElementById('stkModal');
//     const closeSpan = document.querySelector('.close');
//     closeSpan.onclick = closeSTKModal;
//     window.onclick = function(event) {
//         if (event.target == modal) {
//             closeSTKModal();
//         }
//     };

//     // Your existing timer for elapsed time (if any)
//     updateElapsedTimes();
//     setInterval(updateElapsedTimes, 1000);

//     // Placeholder for endSession (implement your logic, e.g., AJAX to end session)
//     window.endSession = function(btn) {
//         const row = btn.closest('tr');
//         const sessionId = row.dataset.sessionId;
//         if (confirm('End this session?')) {
//             // AJAX call to end session endpoint
//             fetch(`/end-session/${sessionId}/`, { method: 'POST', headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value } })
//             .then(() => {
//                 row.style.opacity = '0.5';
//                 row.querySelector('.stk-btn').disabled = false;  // Enable STK after ending
//             })
//             .catch(() => alert('Error ending session'));
//         }
//     };
// });

// // Function to update elapsed times (example; adjust to your needs)
// function updateElapsedTimes() {
//     document.querySelectorAll('.session-row').forEach(row => {
//         const startStr = row.dataset.start;
//         const start = new Date(startStr);
//         const now = new Date();
//         const diff = now - start;
//         const hours = Math.floor(diff / 3600000);
//         const minutes = Math.floor((diff % 3600000) / 60000);
//         const seconds = Math.floor((diff % 60000) / 1000);
//         row.querySelector('.elapsed').textContent = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        
//         // Update amount (e.g., 50 KSH per hour)
//         const amount = (diff / 3600000) * 50;
//         row.querySelector('.amount').textContent = `${amount.toFixed(2)} KSH`;
//     });
// }
