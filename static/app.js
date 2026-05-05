const revealItems = document.querySelectorAll("[data-reveal]");

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
      }
    });
  },
  { threshold: 0.16 }
);

revealItems.forEach((item, index) => {
  item.style.setProperty("--delay", `${Math.min(index * 70, 420)}ms`);
  observer.observe(item);
});

document.querySelectorAll(".inspiration-card").forEach((card) => {
  card.addEventListener("pointermove", (event) => {
    const rect = card.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 100;
    const y = ((event.clientY - rect.top) / rect.height) * 100;
    card.style.setProperty("--x", `${x}%`);
    card.style.setProperty("--y", `${y}%`);
  });
});

const countdown = document.querySelector("#countdown");
if (countdown) {
  let seconds = 600;
  setInterval(() => {
    seconds = Math.max(0, seconds - 1);
    const minutes = String(Math.floor(seconds / 60)).padStart(2, "0");
    const rest = String(seconds % 60).padStart(2, "0");
    countdown.textContent = `${minutes}:${rest}`;
  }, 1000);
}
