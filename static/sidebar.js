document.addEventListener('DOMContentLoaded', function() {
    // Mobile sidebar toggle
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.minimal-sidebar');
    const sidebarOverlay = document.querySelector('.sidebar-overlay');
    
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('active');
            sidebarOverlay.classList.toggle('active');
        });
        
        sidebarOverlay.addEventListener('click', function() {
            sidebar.classList.remove('active');
            sidebarOverlay.classList.remove('active');
        });
    }
    
    // Dropdown functionality
    const dropdownToggles = document.querySelectorAll('.dropdown-toggle');
    
    dropdownToggles.forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const dropdownMenu = this.closest('.nav-dropdown').querySelector('.dropdown-menu');
            const isActive = this.classList.contains('active');
            
            // Close all other dropdowns
            dropdownToggles.forEach(otherToggle => {
                if (otherToggle !== this) {
                    otherToggle.classList.remove('active');
                    otherToggle.closest('.nav-dropdown').querySelector('.dropdown-menu').classList.remove('open');
                }
            });
            
            // Toggle current dropdown
            if (isActive) {
                this.classList.remove('active');
                dropdownMenu.classList.remove('open');
            } else {
                this.classList.add('active');
                dropdownMenu.classList.add('open');
            }
        });
    });
    
    // Close dropdowns when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.nav-dropdown')) {
            dropdownToggles.forEach(toggle => {
                toggle.classList.remove('active');
                toggle.closest('.nav-dropdown').querySelector('.dropdown-menu').classList.remove('open');
            });
        }
    });
    
    // Set active state for bottom nav based on current page
    const currentPath = window.location.pathname;
    const bottomNavLinks = document.querySelectorAll('.bottom-nav-link');
    
    bottomNavLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href && currentPath.includes(href.split('/').filter(Boolean)[0] || '')) {
            link.classList.add('active');
        }
    });
    
    // Auto-close sidebar on mobile when clicking a link
    const navLinks = document.querySelectorAll('.nav-link, .dropdown-link');
    
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                sidebar.classList.remove('active');
                sidebarOverlay.classList.remove('active');
            }
        });
    });
    
    // Highlight current page in sidebar
    const desktopNavLinks = document.querySelectorAll('.nav-link[href], .dropdown-link[href]');
    
    desktopNavLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href && currentPath === href) {
            link.classList.add('active');
            
            // Open parent dropdown if it exists
            const dropdownParent = link.closest('.dropdown-menu');
            if (dropdownParent) {
                dropdownParent.classList.add('open');
                const parentToggle = dropdownParent.closest('.nav-dropdown').querySelector('.dropdown-toggle');
                if (parentToggle) {
                    parentToggle.classList.add('active');
                }
            }
        }
    });
    
    // Initialize tooltips for bottom nav icons
    const tooltips = {
        'home': 'Dashboard',
        'appointment': 'Appointments',
        'course': 'Courses',
        'files': 'Files',
        'user': 'Profile'
    };
    
    const bottomNavIcons = document.querySelectorAll('.bottom-nav-link');
    bottomNavIcons.forEach(link => {
        const type = link.getAttribute('data-nav-type');
        if (type && tooltips[type]) {
            link.setAttribute('title', tooltips[type]);
        }
    });
});