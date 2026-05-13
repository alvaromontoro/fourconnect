document.querySelector("body").classList.add("loaded");

const toggleButton = document.querySelector("#menu-toggle");
const navLinks = document.querySelector("#main-menu");

toggleButton.addEventListener("click", () => {
  navLinks.classList.toggle("active");
  const expanded = toggleButton.getAttribute("aria-expanded") === "true" || false;
  toggleButton.setAttribute("aria-expanded", !expanded);
});

document.body.addEventListener("click", (event) => {
  // close the menu if the click is outside of the nav links and toggle button
  if (!navLinks.contains(event.target) && !toggleButton.contains(event.target)) {
    navLinks.classList.remove("active");
    toggleButton.setAttribute("aria-expanded", "false");
  }
});

document.body.addEventListener("keydown", (event) => {
  // close the menu if the Escape key is pressed
  if (event.key === "Escape") {
    navLinks.classList.remove("active");
    toggleButton.setAttribute("aria-expanded", "false");
  }
});