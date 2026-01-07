// static/js/comments.js
document.addEventListener('DOMContentLoaded', function() {
    // ======================
    // 1. COMMENT SUBMISSION
    // ======================
    const commentForm = document.getElementById('comment-form');
    if (commentForm) {
        commentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            submitFormData(this, '{% url "add_comment" %}', (data) => {
                // Clear form
                this.reset();
                
                // Create new comment element
                const commentsList = document.getElementById('comments-list');
                const emptyMsg = commentsList.querySelector('.text-muted');
                if (emptyMsg) emptyMsg.remove();
                
                const commentDiv = document.createElement('div');
                commentDiv.className = 'comment mb-3';
                commentDiv.id = `comment-${data.comment_id}`;
                commentDiv.innerHTML = `
                    <div class="card">
                        <div class="card-body">
                            <div class="d-flex justify-content-between">
                                <h6 class="card-subtitle mb-2 text-muted">${data.username}</h6>
                                <small class="text-muted">${data.created_at}</small>
                            </div>
                            <p class="card-text">${data.content}</p>
                            <div class="d-flex align-items-center">
                                <button class="btn btn-sm btn-outline-primary like-btn" data-comment-id="${data.comment_id}">
                                    <span class="like-count">${data.like_count}</span> 
                                    <i class="far fa-thumbs-up"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-secondary ms-2 reply-btn" data-comment-id="${data.comment_id}">
                                    Reply
                                </button>
                            </div>
                            <div class="reply-form mt-3" id="reply-form-${data.comment_id}" style="display: none;">
                                <form class="reply-form-inner">
                                    <input type="hidden" name="parent_id" value="${data.comment_id}">
                                    <textarea name="content" rows="2" class="form-control" placeholder="Write a reply..." required></textarea>
                                    <button type="submit" class="btn btn-primary btn-sm mt-2">Post Reply</button>
                                </form>
                            </div>
                            <div class="replies mt-3 ms-4"></div>
                        </div>
                    </div>
                `;
                
                commentsList.prepend(commentDiv);
                initializeCommentEvents(commentDiv);
            });
        });
    }

    // ======================
    // 2. REPLY FUNCTIONALITY
    // ======================
    document.addEventListener('click', function(e) {
        // Show/hide reply form
        if (e.target.classList.contains('reply-btn') || e.target.closest('.reply-btn')) {
            const btn = e.target.closest('.reply-btn');
            const commentId = btn.dataset.commentId;
            const replyForm = document.getElementById(`reply-form-${commentId}`);
            replyForm.style.display = replyForm.style.display === 'none' ? 'block' : 'none';
        }
    });

    // Handle reply form submission (delegated)
    document.addEventListener('submit', function(e) {
        if (e.target.classList.contains('reply-form-inner')) {
            e.preventDefault();
            submitFormData(e.target, '{% url "add_reply" %}', (data) => {
                // Hide form and reset
                const form = e.target;
                form.reset();
                form.closest('.reply-form').style.display = 'none';
                
                // Add new reply to the list
                const repliesContainer = form.closest('.comment').querySelector('.replies');
                const replyDiv = document.createElement('div');
                replyDiv.className = 'reply mb-2';
                replyDiv.id = `reply-${data.reply_id}`;
                replyDiv.innerHTML = `
                    <div class="card">
                        <div class="card-body py-2">
                            <div class="d-flex justify-content-between">
                                <h6 class="card-subtitle mb-1 text-muted">${data.username}</h6>
                                <small class="text-muted">${data.created_at}</small>
                            </div>
                            <p class="card-text mb-1">${data.content}</p>
                            <button class="btn btn-sm btn-outline-primary like-btn" data-comment-id="${data.reply_id}">
                                <span class="like-count">${data.like_count}</span> 
                                <i class="far fa-thumbs-up"></i>
                            </button>
                        </div>
                    </div>
                `;
                
                repliesContainer.appendChild(replyDiv);
                initializeCommentEvents(replyDiv);
            });
        }
    });

    // ======================
    // 3. LIKE FUNCTIONALITY
    // ======================
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('like-btn') || e.target.closest('.like-btn')) {
            const btn = e.target.closest('.like-btn');
            const commentId = btn.dataset.commentId;
            
            fetch('{% url "toggle_like" %}', {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCSRFToken(),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ comment_id: commentId })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const likeCountSpan = btn.querySelector('.like-count');
                    likeCountSpan.textContent = data.like_count;
                    
                    const icon = btn.querySelector('i');
                    btn.classList.toggle('btn-outline-primary', !data.liked);
                    btn.classList.toggle('btn-primary', data.liked);
                    icon.classList.toggle('far', !data.liked);
                    icon.classList.toggle('fas', data.liked);
                } else {
                    showError(data.error || 'Failed to like comment');
                }
            });
        }
    });

    // ======================
    // HELPER FUNCTIONS
    // ======================
    function submitFormData(form, url, onSuccess) {
        const formData = new FormData(form);
        
        fetch(url, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': formData.get('csrfmiddlewaretoken')
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                onSuccess(data);
            } else {
                showError(data.errors ? Object.values(data.errors).join('\n') : 'Action failed');
            }
        })
        .catch(error => {
            showError('Network error. Please try again.');
        });
    }

    function initializeCommentEvents(element) {
        // Add event listeners to any new comment/reply elements
        const likeBtn = element.querySelector('.like-btn');
        if (likeBtn) {
            likeBtn.addEventListener('click', function() {
                // Handled by delegated event listener
            });
        }
        
        const replyBtn = element.querySelector('.reply-btn');
        if (replyBtn) {
            replyBtn.addEventListener('click', function() {
                // Handled by delegated event listener
            });
        }
        
        const replyForm = element.querySelector('.reply-form-inner');
        if (replyForm) {
            replyForm.addEventListener('submit', function(e) {
                // Handled by delegated event listener
            });
        }
    }

    function getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }

    function showError(message) {
        // Implement your error display (could be toast, alert, or inline message)
        console.error(message);
        alert(message); // Replace with your preferred error display
    }

    // Initialize events for existing comments on page load
    document.querySelectorAll('.comment').forEach(initializeCommentEvents);
});