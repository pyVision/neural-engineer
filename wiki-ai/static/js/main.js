/**
 * Main JavaScript file for DeepWiki Clone
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips if Bootstrap is loaded
    if (typeof bootstrap !== 'undefined') {
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Handle navigation highlighting
    function highlightCurrentSection() {
        const scrollPosition = window.scrollY;
        
        // Only run on the repo page if the navigation exists
        const navigation = document.getElementById('repo-navigation');
        if (!navigation) return;
        
        const sections = document.querySelectorAll('.content-section');
        sections.forEach(section => {
            const sectionTop = section.offsetTop - 100;
            const sectionBottom = sectionTop + section.offsetHeight;
            
            if (scrollPosition >= sectionTop && scrollPosition < sectionBottom) {
                const id = section.getAttribute('id');
                const navLink = document.querySelector(`#repo-navigation a[href="#${id}"]`);
                
                document.querySelectorAll('#repo-navigation a').forEach(link => {
                    link.classList.remove('active');
                });
                
                if (navLink) {
                    navLink.classList.add('active');
                }
            }
        });
    }

    // Add scroll event listener
    window.addEventListener('scroll', highlightCurrentSection);
    
    // Initial highlight
    highlightCurrentSection();
});
