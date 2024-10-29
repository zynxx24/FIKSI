const sections = document.querySelectorAll('.content-section');
const menuLinks = document.querySelectorAll('#sidebar .side-menu li a');

menuLinks.forEach(link => {
    link.addEventListener('click', function (e) {
        e.preventDefault();
        sections.forEach(section => section.classList.add('hidden'));
        document.getElementById(link.getAttribute('data-target')).classList.remove('hidden');
        menuLinks.forEach(l => l.parentElement.classList.remove('active'));
        link.parentElement.classList.add('active');
    });
});