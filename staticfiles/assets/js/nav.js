document.addEventListener('DOMContentLoaded', () => {
    const menuButton = document.getElementById('menuButton');
    const dropdownMenu = document.getElementById('dropdownMenu');

    menuButton.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdownMenu.style.display = dropdownMenu.style.display === 'block' ? 'none' : 'block';
    });

    document.addEventListener('click', () => {
        dropdownMenu.style.display = 'none';
    });
});

document.getElementById('menuButton1').addEventListener('click', function () {
    const dropdownMenu = document.getElementById('dropdownMenu1');
    dropdownMenu.classList.toggle('show');
});

document.getElementById('menuButton2').addEventListener('click', function () {
    const dropdownMenu = document.getElementById('dropdownMenu2');
    dropdownMenu.classList.toggle('show');
});

document.getElementById('menuButton3').addEventListener('click', function () {
    const dropdownMenu = document.getElementById('dropdownMenu3');
    dropdownMenu.classList.toggle('show');
});

document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        document.querySelector(this.getAttribute('href')).scrollIntoView({
            behavior: 'smooth'
        });
    });
});

function fetchSearchResults() {
    const searchQuery = document.getElementById("searchInput").value;
    const resultsContainer = document.getElementById("searchResults");

    // Clear results if query is empty
    if (!searchQuery) {
        resultsContainer.innerHTML = "<p class='dropdown-item'>Start typing to search...</p>";
        return;
    }

    // Send AJAX request
    fetch("{% url 'general_search_view' %}", {
        method: "POST",
        headers: {
            "X-CSRFToken": "{{ csrf_token }}",
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ action: "post", ss: searchQuery })
    })
    .then(response => response.json())
    .then(data => {
        const results = JSON.parse(data.search_string);
        if (results.length > 0) {
            resultsContainer.innerHTML = results.map(item => `
                <a href="/detail/${item.pk}" class="dropdown-item">
                    ${item.fields.Full_Names}
                </a>
            `).join('');
        } else {
            resultsContainer.innerHTML = "<p class='dropdown-item'>No results found.</p>";
        }
    })
    .catch(error => {
        console.error("Error fetching search results:", error);
        resultsContainer.innerHTML = "<p class='dropdown-item'>Error fetching results.</p>";
    });
}
