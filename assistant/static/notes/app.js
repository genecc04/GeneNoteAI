// Shared elements and helpers

// Note modal elements (the "+ New note" popup)
const modalOverlay = document.getElementById('note-modal-overlay');
const modalBody = document.getElementById('note-modal-body');
const modalClose = document.getElementById('note-modal-close');

// Read a cookie by name; used to get Django's CSRF token for POST requests
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

// Replace the main panel with a spinner and a message while waiting on the server
function showLoading(message) {
    document.getElementById('main-panel').innerHTML = `
        <div class="loading-box">
            <div class="spinner"></div>
            <p>${message}</p>
        </div>
    `;
}

// Put HTML into the main panel, then draw any formulas inside it
function setMainPanel(html) {
    const panel = document.getElementById('main-panel');
    panel.innerHTML = html;
    renderMath(panel);
}


// Sidebar: Notes / Chats tab switching

// Clicking a tab highlights it and shows only its matching panel
document.querySelectorAll('.sidebar-tab').forEach(function(tab) {
    tab.addEventListener('click', function() {
        document.querySelectorAll('.sidebar-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(p => p.style.display = 'none');

        tab.classList.add('active');
        document.getElementById('tab-' + tab.dataset.tab).style.display = 'block';
    });
});


// Modal: "+ New note" popup

// Fetch the note form and show it in the modal instead of navigating away
document.querySelector('.new-note-btn').addEventListener('click', function(e) {
    e.preventDefault();
    fetch(this.getAttribute('href'), {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(response => response.text())
    .then(html => {
        modalBody.innerHTML = html;
        modalOverlay.classList.add('open');
    });
});

// Close the modal with the X button
modalClose.addEventListener('click', function() {
    modalOverlay.classList.remove('open');
});


// Quiz: submit answers without a page reload

// Forms marked data-quiz-form are sent with fetch; the graded results
// replace the main panel
document.getElementById('main-panel').addEventListener('submit', function(e) {
    const form = e.target;
    if (form.hasAttribute('data-quiz-form')) {
        e.preventDefault();

        showLoading('Grading your quiz...');

        const formData = new FormData(form);

        fetch(form.action, {
            method: 'POST',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            body: formData
        })
        .then(response => response.text())
        .then(html => {
            document.getElementById('main-panel').innerHTML = html;
        });
    }
});


// Notes: open a note/quiz/flashcards link in the main panel

// Any link marked data-note-link (sidebar notes, plus buttons like generate quiz) loads through fetch into the main panel.
document.body.addEventListener('click', function(e) {
    const link = e.target.closest('[data-note-link]');
    if (link) {
        e.preventDefault();
        const url = link.getAttribute('href');

        if (link.hasAttribute('data-generating')) {
                showLoading('Generating with Gemini, please wait...');
            }

        fetch(url, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(response => response.text())
        .then(html => {
            setMainPanel(html);

            // Sidebar active highlight
            window.currentActiveNoteId = link.dataset.noteId;

            document.querySelectorAll('.note-item').forEach(item => item.classList.remove('active'));
            const sidebarItem = document.querySelector(`.note-item[data-note-id="${link.dataset.noteId}"]`);
            if (sidebarItem) sidebarItem.classList.add('active');
        });
    }
});


// Notes sidebar: favorite (star) toggle
document.body.addEventListener('click', function(e) {
    const star = e.target.closest('[data-favorite-btn]');
    if (star) {
        e.preventDefault();
        const noteId = star.dataset.noteId;

        fetch(`/notes/${noteId}/toggle-favorite/`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.text())
        .then(html => {
            document.getElementById('sidebar-list').innerHTML = html;

            // Sidebar active highlight (re-apply after the list re-render)
            const activeItem = document.querySelector(`.note-item[data-note-id="${window.currentActiveNoteId}"]`);
            if (activeItem) activeItem.classList.add('active');
        });
    }
});


// Notes sidebar: delete 

// Confirm, delete on the server, refresh the list. If the deleted note was the one being viewed, go back to the home page.
document.body.addEventListener('click', function(e) {
    const deleteBtn = e.target.closest('[data-delete-btn]');
    if (deleteBtn) {
        e.preventDefault();
        const noteId = deleteBtn.dataset.noteId;

        if (!confirm('Delete this note? This cannot be undone.')) return;

        fetch(`/notes/${noteId}/delete/`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.text())
        .then(html => {
            document.getElementById('sidebar-list').innerHTML = html;

            if (noteId === window.currentActiveNoteId) {
                window.location.href = "/";
            }
        });
    }
});


// Chats sidebar: favorite (star) toggle 

// Same as the notes star, but for the chat list
document.body.addEventListener('click', function(e) {
    const star = e.target.closest('[data-chat-favorite-btn]');
    if (star) {
        e.preventDefault();
        const chatId = star.dataset.chatId;

        fetch(`/chat/${chatId}/toggle-favorite/`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.text())
        .then(html => {
            document.getElementById('sidebar-chats-list').innerHTML = html;

            // Sidebar active highlight (re-apply after the list re-render)
            const activeItem = document.querySelector(`.chat-item[data-chat-id="${window.currentActiveChatId}"]`);
            if (activeItem) activeItem.classList.add('active');
        });
    }
});


// Chats sidebar: delete
document.body.addEventListener('click', function(e) {
    const deleteBtn = e.target.closest('[data-chat-delete-btn]');
    if (deleteBtn) {
        e.preventDefault();
        const chatId = deleteBtn.dataset.chatId;

        if (!confirm('Delete this chat? This cannot be undone.')) return;

        fetch(`/chat/${chatId}/delete/`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.text())
        .then(html => {
            document.getElementById('sidebar-chats-list').innerHTML = html;

            if (chatId === window.currentActiveChatId) {
                window.location.href = "/";
            }
        });
    }
});


// Note forms: submit through fetch 
document.body.addEventListener('submit', function(e) {
    const form = e.target;
    if (form.hasAttribute('data-note-link-form')) {
        e.preventDefault();

        showLoading('Saving...');

        const formData = new FormData(form);

        fetch(form.action, {
            method: 'POST',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            body: formData
        })
        .then(response => response.text())
        .then(html => {
            setMainPanel(html);
        });
    }
});


// Flashcards: flip a card 
document.body.addEventListener('click', function(e) {
    const flipCard = e.target.closest('[data-flip-card]');
    if (flipCard) {
        const front = flipCard.querySelector('.flashcard-front');
        const back = flipCard.querySelector('.flashcard-back');
        if (back.style.display === 'none') {
            front.style.display = 'none';
            back.style.display = 'block';
        } else {
            front.style.display = 'block';
            back.style.display = 'none';
        }
    }
});


// Flashcards: next / previous page 
document.body.addEventListener('click', function(e) {
    if (e.target.id === 'next-page' || e.target.id === 'prev-page') {
        const container = document.getElementById('flashcard-pages');
        const pages = container.querySelectorAll('.flashcard-page');
        let currentPage = parseInt(container.dataset.currentPage);

        pages[currentPage].style.display = 'none';

        if (e.target.id === 'next-page') {
            currentPage++;
        } else {
            currentPage--;
        }

        pages[currentPage].style.display = 'grid';
        container.dataset.currentPage = currentPage;

        document.getElementById('page-counter').textContent = `Page ${currentPage + 1} of ${pages.length}`;
        document.getElementById('prev-page').disabled = (currentPage === 0);
        document.getElementById('next-page').disabled = (currentPage === pages.length - 1);
    }
});


// Chat: edit the chat title
function setTitleEditing(editing) {
    document.getElementById('chat-title-view').style.display = editing ? 'none' : 'flex';
    document.getElementById('chat-title-edit').style.display = editing ? 'flex' : 'none';
}

// ---------- Chat: send a message without reloading ----------

// True while a reply is pending; blocks a second send
let isSending = false;

// Turn plain text into safe HTML (escape < > &, keep line breaks)
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML.replace(/\n/g, '<br>');
}

// Add a bubble to the bottom of the chat, scroll to it, and return the new row
function appendMessage(role, html) {
    const box = document.getElementById('chat-messages');
    const row = document.createElement('div');
    row.className = `chat-message ${role}`;
    row.innerHTML = `<div class="chat-bubble">${html}</div>`;
    box.appendChild(row);
    box.scrollTop = box.scrollHeight;
    return row;
}

// Handle the chat form: show the message and thinking dots, send it in the
// background, then swap the dots for the reply (or an error)
document.body.addEventListener('submit', async function(e) {
    if (e.target.id !== 'chat-form') return;
    e.preventDefault();
    if (isSending) return;

    const input = document.getElementById('chat-input');
    const sendBtn = e.target.querySelector('.chat-send-btn');
    const chatId = document.querySelector('.chat-header').dataset.chatId;
    const text = input.value.trim();
    if (!text) return;

    // Lock the form until the reply arrives
    isSending = true;
    sendBtn.disabled = true;
    input.readOnly = true;
    input.placeholder = 'Waiting for reply...';

    // Remove an earlier error, then show your message and the thinking dots
    document.querySelectorAll('.chat-message.error').forEach(row => row.remove());
    const userRow = appendMessage('user', escapeHtml(text));
    input.value = '';
    input.style.height = 'auto';
    const thinkingRow = appendMessage('model',
        '<span class="typing" aria-label="Thinking"><span></span><span></span><span></span></span>');

    try {
        const formData = new FormData();
        formData.append('message', text);

        const response = await fetch(`/chat/${chatId}/`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: formData
        }).catch(() => null);
        if (!response) throw new Error('Could not reach the server.');

        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || 'Something went wrong. Please try again.');

        // Swap the dots for the formatted reply, then draw any formulas in it
        thinkingRow.querySelector('.chat-bubble').innerHTML =
            `<div class="markdown-body">${data.reply_html}</div>`;
        renderMath(thinkingRow);
        if (data.title) updateChatTitle(chatId, data.title);
    } catch (error) {
        // Nothing was saved on the server, so undo the screen too and give the text back
        userRow.remove();
        thinkingRow.remove();
        input.value = text;
        input.dispatchEvent(new Event('input'));
        appendMessage('model', escapeHtml(error.message)).classList.add('error');
    } finally {
        // Unlock the form whether it worked or not
        isSending = false;
        sendBtn.disabled = false;
        input.readOnly = false;
        input.placeholder = 'Type a message...';
        input.focus();
        const box = document.getElementById('chat-messages');
        box.scrollTop = box.scrollHeight;
    }
});

// Update the chat title in the page heading and in the sidebar entry
function updateChatTitle(chatId, title) {
    document.getElementById('chat-title').textContent = title;

    const sidebarTitle = document.querySelector(`.chat-item[data-chat-id="${chatId}"] .note-title`);
    if (sidebarTitle) sidebarTitle.textContent = title;
}

// Send the new title to the server, then update the heading and the matching sidebar entry in place (no reload)
function saveChatTitle() {
    const chatId = document.querySelector('.chat-header').dataset.chatId;
    const newTitle = document.getElementById('chat-title-input').value.trim();
    if (!newTitle) return;

    const formData = new FormData();
    formData.append('title', newTitle);

    fetch(`/chat/${chatId}/rename/`, {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
                updateChatTitle(chatId, data.title);
                setTitleEditing(false);
            });
}

// Edit / Cancel / Save buttons in the chat header
document.body.addEventListener('click', function(e) {
    if (e.target.id === 'edit-chat-title-btn') {
        const input = document.getElementById('chat-title-input');
        input.value = document.getElementById('chat-title').textContent;
        setTitleEditing(true);
        input.focus();
        input.select();
    }
    if (e.target.id === 'cancel-chat-title-btn') setTitleEditing(false);
    if (e.target.id === 'save-chat-title-btn') saveChatTitle();
});

// Keyboard shortcuts inside the title input: Enter saves, Escape cancels
document.body.addEventListener('keydown', function(e) {
    if (e.target.id === 'chat-title-input') {
        if (e.key === 'Enter') { e.preventDefault(); saveChatTitle(); }
        if (e.key === 'Escape') setTitleEditing(false);
    }
});


// Math: draw LaTeX formulas with KaTeX 
function renderMath(root) {
    root.querySelectorAll('.math').forEach(function(el) {
        if (el.dataset.rendered) return;
        katex.render(el.textContent, el, {
            displayMode: el.tagName === 'DIV',
            throwOnError: false
        });
        el.dataset.rendered = 'true';
    });
}

// Run once when the page loads
renderMath(document);


// Chat: start scrolled to the newest message 

// Runs after the math is drawn, because formulas change message heights
const chatBox = document.getElementById('chat-messages');
if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;

// Settings: open in the main panel and save

// Load the settings page into the main panel and clear the sidebar highlight
document.getElementById('open-settings-btn').addEventListener('click', function() {
    fetch('/settings/', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(response => response.text())
        .then(html => {
            document.getElementById('main-panel').innerHTML = html;

            // Nothing is the "current" note or chat while settings are open
            window.currentActiveNoteId = '';
            window.currentActiveChatId = '';
            document.querySelectorAll('.note-item, .chat-item').forEach(item => item.classList.remove('active'));
        });
});

// Save: the server sends the form back with "Settings saved" or with error messages
document.body.addEventListener('submit', function(e) {
    if (e.target.id !== 'settings-form') return;
    e.preventDefault();

    fetch(e.target.action, {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: new FormData(e.target)
    })
    .then(response => response.text())
    .then(html => {
        const panel = document.getElementById('main-panel');
        panel.innerHTML = html;
        panel.scrollTop = 0;
    });
});

// Note settings: open the popup and save

// Open this note's settings in the modal
document.body.addEventListener('click', function(e) {
    const btn = e.target.closest('[data-note-settings-btn]');
    if (!btn) return;

    fetch(`/notes/${btn.dataset.noteId}/settings/`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(response => response.text())
    .then(html => {
        modalBody.innerHTML = html;
        modalOverlay.classList.add('open');
    });
});

// Save: on success close the popup; on a validation error, show the form again with the messages
document.body.addEventListener('submit', function(e) {
    if (e.target.id !== 'note-settings-form') return;
    e.preventDefault();

    fetch(e.target.action, {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: new FormData(e.target)
    })
    .then(response => {
        if (response.ok) {
            modalOverlay.classList.remove('open');
            return null;
        }
        return response.text();
    })
    .then(html => {
        if (html) modalBody.innerHTML = html;
    });
});

// Individual settings popups (notes and chats share this code)

// Fetch a settings form and show it in the modal
function openSettingsModal(url) {
    fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(response => response.text())
        .then(html => {
            modalBody.innerHTML = html;
            modalOverlay.classList.add('open');
        });
}

// The two open buttons only differ in their URL
document.body.addEventListener('click', function(e) {
    const noteBtn = e.target.closest('[data-note-settings-btn]');
    if (noteBtn) openSettingsModal(`/notes/${noteBtn.dataset.noteId}/settings/`);

    const chatBtn = e.target.closest('[data-chat-settings-btn]');
    if (chatBtn) openSettingsModal(`/chat/${chatBtn.dataset.chatId}/settings/`);
});

// Save either form: on success close the popup; on a validation error, show the form again with the messages
document.body.addEventListener('submit', function(e) {
    if (e.target.id !== 'note-settings-form' && e.target.id !== 'chat-settings-form') return;
    e.preventDefault();

    fetch(e.target.action, {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: new FormData(e.target)
    })
    .then(response => {
        if (response.ok) {
            modalOverlay.classList.remove('open');
            return null;
        }
        return response.text();
    })
    .then(html => {
        if (html) modalBody.innerHTML = html;
    });
});