 document.addEventListener('DOMContentLoaded', () => {
        const contactForm = document.querySelector('form');
        if (contactForm) {
            contactForm.addEventListener('submit', (e) => {
                setTimeout(() => {
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                }, 500);
            });
        }
    });