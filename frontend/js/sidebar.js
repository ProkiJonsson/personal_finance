/**
 * Sidebar Toggle Functionality
 * Pure JS implementation for sidebar collapse/expand
 */

(function() {
    'use strict';

    // Initialize sidebar when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        initSidebar();
    });

    function initSidebar() {
        const sidebar = document.querySelector('.sidebar');
        const toggleBtn = document.querySelector('.sidebar-toggle');

        if (!sidebar || !toggleBtn) return;

        // Check saved state from localStorage
        const savedState = localStorage.getItem('sidebarExpanded');
        if (savedState === 'true') {
            sidebar.classList.add('expanded');
            document.body.classList.add('sidebar-expanded');
        }

        // Toggle on button click
        toggleBtn.addEventListener('click', function() {
            const isExpanded = sidebar.classList.toggle('expanded');
            document.body.classList.toggle('sidebar-expanded', isExpanded);
            
            // Save state to localStorage
            localStorage.setItem('sidebarExpanded', isExpanded);
        });

        // Set active nav item based on current page
        setActiveNavItem();
    }

    function setActiveNavItem() {
        const currentPage = window.location.pathname.split('/').pop() || 'index.html';
        const navItems = document.querySelectorAll('.nav-item');

        navItems.forEach(function(item) {
            const href = item.getAttribute('href');
            if (href === currentPage || 
                (currentPage === '' && href === 'dashboard.html') ||
                (currentPage === 'dashboard.html' && href === 'dashboard.html')) {
                item.classList.add('active');
            }
        });
    }

    // Handle logout
    window.handleLogout = function() {
        localStorage.removeItem('token');
        sessionStorage.removeItem('token');
        window.location.href = 'index.html';
    };
})();
