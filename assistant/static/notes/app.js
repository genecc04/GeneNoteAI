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
            document.getElementById('main-panel').innerHTML = html;

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
            document.getElementById('main-panel').innerHTML = html;
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
        document.getElementById('chat-title').textContent = data.title;

        const sidebarTitle = document.querySelector(`.chat-item[data-chat-id="${chatId}"] .note-title`);
        if (sidebarTitle) sidebarTitle.textContent = data.title;

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