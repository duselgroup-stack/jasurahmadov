/* ══ Scroll'da ochilish — iOS uslubidagi ketma-ket "spring" ══ */
const io = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.classList.add('in');
      io.unobserve(e.target);
    }
  });
}, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });

document.querySelectorAll('.reveal').forEach((el, i) => {
  el.style.transitionDelay = (i % 4) * 80 + 'ms';
  io.observe(el);
});

/* ══ Liquid glass: kursor ortidan yuradigan yorug'lik ══ */
document.querySelectorAll('.glass').forEach(el => {
  el.addEventListener('pointermove', e => {
    const r = el.getBoundingClientRect();
    el.style.setProperty('--mx', ((e.clientX - r.left) / r.width * 100) + '%');
    el.style.setProperty('--my', ((e.clientY - r.top) / r.height * 100) + '%');
  });
});

/* ══ Hero rasm: sichqoncha ortidan yengil parallaks ══ */
const visual = document.querySelector('.hero-visual');
if (visual && matchMedia('(pointer:fine)').matches) {
  const photo = visual.querySelector('.hero-photo');
  visual.addEventListener('pointermove', e => {
    const r = visual.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - .5;
    const y = (e.clientY - r.top) / r.height - .5;
    photo.style.transform = `perspective(900px) rotateY(${x * 7}deg) rotateX(${-y * 7}deg)`;
  });
  visual.addEventListener('pointerleave', () => {
    photo.style.transform = '';
  });
}

/* ══ Header: pastga scroll qilinganda material quyuqlashadi ══ */
const head = document.querySelector('.site-head');
addEventListener('scroll', () => {
  head.style.boxShadow = scrollY > 20
    ? 'inset 0 1px 0 rgba(255,255,255,.3), 0 14px 40px rgba(2,8,20,.6)'
    : '';
}, { passive: true });

/* ══ Rasm hali qo'yilmagan bo'lsa — toza joy egallovchi ══ */
function markEmpty(img){
  const box = img.parentElement;
  // fayl nomini ko'rsatib qo'yamiz — qaysi rasmni qo'yish kerakligi bilinadi
  box.dataset.file = img.getAttribute('src');
  box.classList.add('img-empty');
  img.remove();
}

document.querySelectorAll('figure img').forEach(img => {
  img.addEventListener('error', () => markEmpty(img));
  // skript yuklanguncha yiqilib bo'lgan rasmlar uchun
  if (img.complete && img.naturalWidth === 0) markEmpty(img);
});
