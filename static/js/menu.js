document.addEventListener('DOMContentLoaded', () => {
  const openBtn = document.getElementById('open-menu-button');
  const closeBtns = document.querySelectorAll('.close-menu-button');
  const menu = document.getElementById('side-menu');
  const overlay = document.getElementById('overlay');

  const openMenu = () => {
    menu.classList.remove('-translate-x-full');
    overlay.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  };

  const closeMenu = () => {
    menu.classList.add('-translate-x-full');
    overlay.classList.add('hidden');
    document.body.style.overflow = '';
  };

  openBtn?.addEventListener('click', openMenu);
  overlay?.addEventListener('click', closeMenu);
  closeBtns.forEach(btn => btn.addEventListener('click', closeMenu));
});
